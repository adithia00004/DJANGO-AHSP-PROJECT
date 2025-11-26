# =====================================================================
# FILE: detail_project/exports/jadwal_pekerjaan_adapter.py
# =====================================================================
"""
Jadwal Pekerjaan export adapter.

This adapter transforms the canonical weekly progress data into a pair of
tables (weekly + monthly aggregation) that mirror the Jadwal Pekerjaan grid.
Weekly is the canonical scale, while monthly columns simply aggregate every
four weeks (last block may contain <4 columns).
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Dict, List, Sequence, Tuple

from django.db.models import Prefetch

from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    TahapPelaksanaan,
    VolumePekerjaan,
)
from detail_project.progress_utils import calculate_week_number, get_week_date_range
from ..export_config import get_page_size_mm


class JadwalPekerjaanExportAdapter:
    """Data adapter for Jadwal Pekerjaan (weekly + monthly export)."""

    def __init__(
        self,
        project,
        include_monthly: bool = True,
        page_size: str = 'A4',
        page_orientation: str = 'landscape',
        margin_left: int = 10,
        margin_right: int = 10,
    ):
        self.project = project
        self.include_monthly = include_monthly
        self.project_start: date | None = None
        self.project_end: date | None = None
        self.page_size = (page_size or 'A4').upper()
        orientation = (page_orientation or 'landscape').lower()
        if orientation not in ('portrait', 'landscape'):
            orientation = 'landscape'
        self.page_orientation = orientation
        self.margin_left = margin_left
        self.margin_right = margin_right

        base_width_mm, base_height_mm = get_page_size_mm(self.page_size)
        if self.page_orientation == 'portrait':
            self.page_width_mm = base_width_mm
            self.page_height_mm = base_height_mm
        else:
            self.page_width_mm = base_height_mm
            self.page_height_mm = base_width_mm

        self.usable_width_mm = max(150.0, self.page_width_mm - (self.margin_left + self.margin_right))
        self.scale_factor = max(self.usable_width_mm / 277.0, 0.5)
        self.static_widths_mm = [
            28 * self.scale_factor,  # Kode
            95 * self.scale_factor,  # Uraian
            25 * self.scale_factor,  # Volume
            20 * self.scale_factor,  # Satuan
        ]
        self.static_width_sum = sum(self.static_widths_mm)
        self.min_weekly_col_width_mm = 28 * self.scale_factor
        self.min_monthly_col_width_mm = 40 * self.scale_factor
        self.weekly_columns_per_page = self._compute_columns_per_page(
            self.min_weekly_col_width_mm, hard_limit=12
        )
        self.monthly_columns_per_page = self._compute_columns_per_page(
            self.min_monthly_col_width_mm, hard_limit=8
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_export_data(self) -> Dict[str, Any]:
        weekly_tahapan = self._fetch_weekly_tahapan()
        progress_map, progress_meta = self._build_progress_map()

        self.project_start, self.project_end = self._resolve_project_dates(
            weekly_tahapan,
            progress_meta.get("earliest_start"),
            progress_meta.get("latest_end"),
        )

        weekly_columns = self._build_weekly_columns(
            weekly_tahapan, progress_meta.get("max_week_number", 0)
        )
        monthly_columns = self._build_monthly_columns(weekly_columns)

        base_rows, hierarchy = self._build_base_rows()
        pages: List[Dict[str, Any]] = []

        weekly_chunks = self._chunk_columns(weekly_columns, self.weekly_columns_per_page)
        for idx, chunk in enumerate(weekly_chunks, start=1):
            rows = self._materialize_rows(base_rows, chunk, progress_map)
            title = "JADWAL PEKERJAAN - WEEKLY"
            if len(weekly_chunks) > 1:
                title = f"{title} (Bagian {idx})"

            pages.append(
                {
                    "title": title,
                    "table_data": {
                        "headers": self._build_headers(chunk),
                        "rows": rows,
                    },
                    "col_widths": self._build_col_widths(len(chunk)),
                    "hierarchy_levels": hierarchy,
                }
            )

        if self.include_monthly and monthly_columns:
            monthly_chunks = self._chunk_columns(monthly_columns, self.monthly_columns_per_page)
            for idx, chunk in enumerate(monthly_chunks, start=1):
                rows = self._materialize_rows(base_rows, chunk, progress_map)
                title = "JADWAL PEKERJAAN - MONTHLY"
                if len(monthly_chunks) > 1:
                    title = f"{title} (Bagian {idx})"

                pages.append(
                    {
                        "title": title,
                        "table_data": {
                            "headers": self._build_headers(chunk),
                            "rows": rows,
                        },
                        "col_widths": self._build_col_widths(len(chunk)),
                        "hierarchy_levels": hierarchy,
                    }
                )

        return {"pages": pages}

    # ------------------------------------------------------------------
    # Weekly / Monthly column builders
    # ------------------------------------------------------------------
    def _fetch_weekly_tahapan(self) -> List[TahapPelaksanaan]:
        return list(
            TahapPelaksanaan.objects.filter(
                project=self.project,
                is_auto_generated=True,
                generation_mode="weekly",
            ).order_by("urutan", "id")
        )

    def _build_weekly_columns(
        self, weekly_tahapan: Sequence[TahapPelaksanaan], max_week_number: int
    ) -> List[Dict[str, Any]]:
        week_end_day = self._get_week_end_day()
        project_start = self.project_start or date.today()
        expected_weeks = self._estimate_week_count(project_start, self.project_end or project_start)
        target_weeks = max(expected_weeks, max_week_number or 0)
        columns: List[Dict[str, Any]] = []

        for tahap in weekly_tahapan:
            start_date = tahap.tanggal_mulai or project_start
            end_date = tahap.tanggal_selesai or start_date
            week_number = calculate_week_number(start_date, project_start, week_end_day)
            if week_number <= 0:
                week_number = len(columns) + 1
            columns.append(
                {
                    "id": f"week-{week_number:03d}",
                    "field": f"week_{week_number:03d}",
                    "label": f"Week {week_number}",
                    "range": self._format_range_label(start_date, end_date),
                    "week_number": week_number,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )

        if not columns:
            target_weeks = max(1, target_weeks)

        columns = self._ensure_weekly_column_count(columns, target_weeks, project_start, week_end_day)
        return columns

    def _ensure_weekly_column_count(
        self,
        columns: List[Dict[str, Any]],
        target_weeks: int,
        project_start: date,
        week_end_day: int,
    ) -> List[Dict[str, Any]]:
        current = len(columns)
        while current < target_weeks:
            week_number = current + 1
            week_start, week_end = get_week_date_range(week_number, project_start, week_end_day)
            columns.append(
                {
                    "id": f"week-{week_number:03d}",
                    "field": f"week_{week_number:03d}",
                    "label": f"Week {week_number}",
                    "range": self._format_range_label(week_start, week_end),
                    "week_number": week_number,
                    "start_date": week_start,
                    "end_date": week_end,
                }
            )
            current += 1
        if not columns:
            columns.append(
                {
                    "id": "week-001",
                    "field": "week_001",
                    "label": "Week 1",
                    "range": self._format_range_label(project_start, project_start),
                    "week_number": 1,
                    "start_date": project_start,
                    "end_date": project_start,
                }
            )
        return columns

    def _build_monthly_columns(self, weekly_columns: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        block_size = 4
        aggregated: List[Dict[str, Any]] = []

        for index in range(0, len(weekly_columns), block_size):
            block = weekly_columns[index : index + block_size]
            if not block:
                continue
            block_index = len(aggregated) + 1
            child_weeks = [col.get("week_number") for col in block if col.get("week_number")]
            start_week = child_weeks[0]
            end_week = child_weeks[-1]
            aggregated.append(
                {
                    "id": f"month-{block_index:02d}",
                    "field": f"month_{block_index:02d}",
                    "label": f"Month {block_index}",
                    "range": f"Week {start_week}-{end_week}",
                    "child_weeks": child_weeks,
                }
            )

        if not aggregated and self.include_monthly:
            aggregated.append(
                {
                    "id": "month-01",
                    "field": "month_01",
                    "label": "Month 1",
                    "range": "Week 1-4",
                    "child_weeks": [col.get("week_number") for col in weekly_columns[:4] if col.get("week_number")] or [1],
                }
            )

        return aggregated

    # ------------------------------------------------------------------
    # Data builders
    # ------------------------------------------------------------------
    def _build_progress_map(self) -> Tuple[Dict[Tuple[int, int], Decimal], Dict[str, Any]]:
        progress_map: Dict[Tuple[int, int], Decimal] = {}
        max_week_number = 0
        earliest_start: date | None = None
        latest_end: date | None = None

        weekly_qs = PekerjaanProgressWeekly.objects.filter(project=self.project).only(
            "pekerjaan_id", "week_number", "proportion", "week_start_date", "week_end_date"
        )

        for record in weekly_qs:
            key = (record.pekerjaan_id, record.week_number)
            try:
                progress_map[key] = Decimal(record.proportion or 0)
            except InvalidOperation:
                progress_map[key] = Decimal("0")

            if record.week_number and record.week_number > max_week_number:
                max_week_number = record.week_number
            if record.week_start_date and (earliest_start is None or record.week_start_date < earliest_start):
                earliest_start = record.week_start_date
            if record.week_end_date and (latest_end is None or record.week_end_date > latest_end):
                latest_end = record.week_end_date

        return progress_map, {
            "max_week_number": max_week_number,
            "earliest_start": earliest_start,
            "latest_end": latest_end,
        }

    def _resolve_project_dates(
        self,
        weekly_tahapan: Sequence[TahapPelaksanaan],
        earliest_week_start: date | None,
        latest_week_end: date | None,
    ) -> Tuple[date, date]:
        today = date.today()
        start_candidates: List[date] = []
        end_candidates: List[date] = []

        if getattr(self.project, "tanggal_mulai", None):
            start_candidates.append(self.project.tanggal_mulai)
        if earliest_week_start:
            start_candidates.append(earliest_week_start)
        for tahap in weekly_tahapan:
            if tahap.tanggal_mulai:
                start_candidates.append(tahap.tanggal_mulai)

        project_start = min(start_candidates) if start_candidates else today

        if getattr(self.project, "tanggal_selesai", None):
            end_candidates.append(self.project.tanggal_selesai)
        else:
            end_candidates.append(date(project_start.year, 12, 31))

        if latest_week_end:
            end_candidates.append(latest_week_end)
        for tahap in weekly_tahapan:
            if tahap.tanggal_selesai:
                end_candidates.append(tahap.tanggal_selesai)

        project_end = max(end_candidates) if end_candidates else project_start
        if project_end < project_start:
            project_end = project_start

        return project_start, project_end

    def _load_volume_map(self) -> Dict[int, Decimal]:
        volume_map: Dict[int, Decimal] = {}
        volume_qs = VolumePekerjaan.objects.filter(project=self.project).values("pekerjaan_id", "quantity")
        for row in volume_qs:
            volume_map[row["pekerjaan_id"]] = self._to_decimal(row["quantity"])
        return volume_map

    def _build_base_rows(self) -> Tuple[List[Dict[str, Any]], Dict[int, int]]:
        rows: List[Dict[str, Any]] = []
        hierarchy: Dict[int, int] = {}
        row_index = 0
        volume_map = self._load_volume_map()

        pekerjaan_prefetch = Prefetch(
            "pekerjaan_list",
            queryset=Pekerjaan.objects.filter(project=self.project).order_by("ordering_index", "id"),
        )
        sub_prefetch = Prefetch(
            "sub_list",
            queryset=SubKlasifikasi.objects.filter(project=self.project)
            .order_by("ordering_index", "id")
            .prefetch_related(pekerjaan_prefetch),
        )

        klasifikasi_list = (
            Klasifikasi.objects.filter(project=self.project)
            .order_by("ordering_index", "id")
            .prefetch_related(sub_prefetch)
        )

        for klas in klasifikasi_list:
            rows.append(
                {
                    "type": "klasifikasi",
                    "kode": "",
                    "uraian": getattr(klas, "name", getattr(klas, "nama", "Klasifikasi")),
                    "volume_display": "",
                    "unit": "",
                }
            )
            hierarchy[row_index] = 1
            row_index += 1

            for sub in klas.sub_list.all():
                rows.append(
                    {
                        "type": "sub_klasifikasi",
                        "kode": "",
                        "uraian": getattr(sub, "name", getattr(sub, "nama", "Sub-Klasifikasi")),
                        "volume_display": "",
                        "unit": "",
                    }
                )
                hierarchy[row_index] = 2
                row_index += 1

                for pek in sub.pekerjaan_list.all():
                    volume = volume_map.get(pek.id, Decimal("0"))
                    rows.append(
                        {
                            "type": "pekerjaan",
                            "pekerjaan_id": pek.id,
                            "kode": getattr(pek, "snapshot_kode", getattr(pek, "kode_ahsp", "")) or "",
                            "uraian": getattr(pek, "snapshot_uraian", getattr(pek, "nama", "")) or "",
                            "unit": getattr(pek, "snapshot_satuan", getattr(pek, "satuan", "")) or "",
                            "volume_display": self._format_number(volume, 3),
                        }
                    )
                    hierarchy[row_index] = 3
                    row_index += 1

        return rows, hierarchy

    def _materialize_rows(
        self,
        base_rows: Sequence[Dict[str, Any]],
        columns: Sequence[Dict[str, Any]],
        progress_map: Dict[Tuple[int, int], Decimal],
    ) -> List[List[str]]:
        materialized: List[List[str]] = []

        for row in base_rows:
            kode = row.get("kode", "")
            uraian = row.get("uraian", "")
            volume_display = row.get("volume_display", "")
            unit = row.get("unit", "")

            if row.get("type") != "pekerjaan":
                volume_display = ""
                unit = ""

            row_values = [kode, uraian, volume_display, unit]

            pekerjaan_id = row.get("pekerjaan_id")

            for column in columns:
                cell_value = ""
                if pekerjaan_id and row.get("type") == "pekerjaan":
                    child_weeks = column.get("child_weeks")
                    if child_weeks:
                        total = sum(progress_map.get((pekerjaan_id, wk), Decimal("0")) for wk in child_weeks)
                    else:
                        week_number = column.get("week_number")
                        total = progress_map.get((pekerjaan_id, week_number), Decimal("0"))
                    cell_value = self._format_percent(total)
                row_values.append(cell_value)

            materialized.append(row_values)

        return materialized

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _build_headers(self, columns: Sequence[Dict[str, Any]]) -> List[str]:
        headers = ["Kode", "Uraian Pekerjaan", "Volume", "Satuan"]
        for column in columns:
            label = column.get("label") or "Week"
            range_label = column.get("range")
            if range_label:
                headers.append(f"{label} ({range_label})")
            else:
                headers.append(label)
        return headers

    def _build_col_widths(self, time_column_count: int) -> List[float]:
        static_widths = list(self.static_widths_mm)
        if time_column_count <= 0:
            return static_widths
        remaining = max(20.0, self.usable_width_mm - sum(static_widths))
        per_column = remaining / time_column_count
        return static_widths + [per_column] * time_column_count

    def _chunk_columns(
        self, columns: Sequence[Dict[str, Any]], max_per_page: int
    ) -> List[List[Dict[str, Any]]]:
        if max_per_page <= 0:
            max_per_page = len(columns) or 1
        if not columns:
            return [[]]
        return [list(columns[i : i + max_per_page]) for i in range(0, len(columns), max_per_page)]

    def _compute_columns_per_page(self, min_width_mm: float, hard_limit: int) -> int:
        remaining = max(20.0, self.usable_width_mm - self.static_width_sum)
        approx = int(remaining // max(min_width_mm, 1.0))
        approx = max(1, approx)
        if hard_limit > 0:
            return min(approx, hard_limit)
        return approx

    def _estimate_week_count(self, project_start: date, project_end: date) -> int:
        if not project_start or not project_end:
            return 1
        days = max(0, (project_end - project_start).days) + 1
        return max(1, math.ceil(days / 7))

    def _get_week_end_day(self) -> int:
        raw = getattr(self.project, "week_end_day", None)
        if raw is None:
            return 6
        try:
            parsed = int(raw) % 7
            return parsed if parsed >= 0 else parsed + 7
        except (ValueError, TypeError):
            return 6

    def _format_range_label(self, start: date | None, end: date | None) -> str:
        def fmt(value: date | None) -> str:
            if not value:
                return "--/--"
            return value.strftime("%d/%m")

        return f"{fmt(start)} - {fmt(end)}"

    def _format_number(self, value: Any, decimals: int = 2) -> str:
        try:
            if value is None or value == "":
                return "-"
            number = self._to_decimal(value)
            if decimals == 0:
                formatted = f"{int(round(float(number))):,}"
            else:
                formatted = f"{float(number):,.{decimals}f}"
            return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        except (InvalidOperation, ValueError, TypeError):
            return "-"

    def _format_percent(self, value: Decimal | float | int) -> str:
        decimal_value = self._to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formatted = f"{float(decimal_value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"{formatted}%"

    def _to_decimal(self, value: Any) -> Decimal:
        if value is None or value == "":
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError):
            cleaned = str(value).strip()
            if not cleaned:
                return Decimal("0")
            cleaned = cleaned.replace(".", "").replace(",", ".")
            try:
                return Decimal(cleaned)
            except InvalidOperation:
                return Decimal("0")
