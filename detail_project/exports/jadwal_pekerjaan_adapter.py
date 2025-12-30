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
from detail_project.services import compute_rekap_for_project
from ..export_config import get_page_size_mm, JadwalExportLayout
from .table_styles import SectionHeaderFormatter as SHF


class JadwalPekerjaanExportAdapter:
    """Data adapter for Jadwal Pekerjaan (weekly + monthly export)."""

    def __init__(
        self,
        project,
        include_monthly: bool = True,
        page_size: str | None = None,
        page_orientation: str | None = None,
        margin_left: int | None = None,
        margin_right: int | None = None,
        layout_spec=JadwalExportLayout,
        auto_compact_weeks: bool = False,
        weekly_threshold: int | None = None,
        max_rows_per_page: int | None = None,
    ):
        self.project = project
        self.include_monthly = include_monthly
        self._rekap_harga_cache: Dict[int, Decimal] | None = None  # Lazy cache for harga lookup
        self.layout_spec = layout_spec or JadwalExportLayout
        self.auto_compact_weeks = auto_compact_weeks
        self.weekly_threshold = (
            weekly_threshold
            if weekly_threshold is not None
            else getattr(self.layout_spec, "AUTO_MONTHLY_THRESHOLD", JadwalExportLayout.WEEKLY_HARD_LIMIT)
        )
        self.max_rows_per_page = max_rows_per_page or getattr(self.layout_spec, "ROWS_PER_PAGE", 0)
        self.project_start: date | None = None
        self.project_end: date | None = None
        self.page_size = (page_size or getattr(self.layout_spec, "PAGE_SIZE", "A4") or 'A4').upper()
        orientation = (page_orientation or getattr(self.layout_spec, "ORIENTATION", "landscape") or 'landscape').lower()
        if orientation not in ('portrait', 'landscape'):
            orientation = 'landscape'
        self.page_orientation = orientation
        self.margin_left = margin_left if margin_left is not None else getattr(self.layout_spec, "MARGIN_LEFT", 10)
        self.margin_right = margin_right if margin_right is not None else getattr(self.layout_spec, "MARGIN_RIGHT", 10)

        base_width_mm, base_height_mm = get_page_size_mm(self.page_size)
        if self.page_orientation == 'portrait':
            self.page_width_mm = base_width_mm
            self.page_height_mm = base_height_mm
        else:
            self.page_width_mm = base_height_mm
            self.page_height_mm = base_width_mm

        self.usable_width_mm = max(150.0, self.page_width_mm - (self.margin_left + self.margin_right))
        # Use absolute widths tuned for A3; scale lightly if page is narrower
        base_total = self.page_width_mm if self.page_size == 'A3' else 277.0
        self.scale_factor = max(self.usable_width_mm / base_total, 0.6)
        self.static_widths_mm = [
            w * self.scale_factor for w in self.layout_spec.static_widths_mm()
        ]
        self.static_width_sum = sum(self.static_widths_mm)
        self.min_weekly_col_width_mm = getattr(self.layout_spec, "WEEKLY_MIN_COL", 12) * self.scale_factor
        self.min_monthly_col_width_mm = getattr(self.layout_spec, "MONTHLY_MIN_COL", 20) * self.scale_factor
        self.weekly_columns_per_page = self._compute_columns_per_page(
            self.min_weekly_col_width_mm, hard_limit=getattr(self.layout_spec, "WEEKLY_HARD_LIMIT", 12)
        )
        self.monthly_columns_per_page = self._compute_columns_per_page(
            self.min_monthly_col_width_mm, hard_limit=getattr(self.layout_spec, "MONTHLY_HARD_LIMIT", 8)
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
        row_chunks = self._chunk_rows(base_rows, hierarchy, self.max_rows_per_page)
        page_seq = 1

        if weekly_columns:
            for col_idx, chunk in enumerate(weekly_chunks, start=1):
                for row_idx, (row_slice, hierarchy_slice) in enumerate(row_chunks, start=1):
                    rows = self._materialize_rows(row_slice, chunk, progress_map)
                    
                    # Calculate page number and total pages for this section
                    total_weekly_pages = len(weekly_chunks) * len(row_chunks)
                    current_page = (col_idx - 1) * len(row_chunks) + row_idx
                    
                    # Get week range from chunk
                    week_start = chunk[0].get('week', 1) if chunk else 1
                    week_end = chunk[-1].get('week', week_start) if chunk else week_start
                    
                    # Use SHF for consistent header formatting
                    title = SHF.input_progress('PLANNED', current_page, total_weekly_pages, week_start, week_end)

                    pages.append(
                        {
                            "title": title,
                            "table_data": {
                                "headers": self._build_headers(chunk),
                                "rows": rows,
                            },
                            "col_widths": self._build_col_widths(len(chunk)),
                            "hierarchy_levels": hierarchy_slice,
                            "meta": {
                                "mode": "weekly",
                                "page_seq": page_seq,
                                "column_chunk": col_idx,
                                "row_chunk": row_idx,
                            },
                        }
                    )
                    page_seq += 1

        if self.include_monthly and monthly_columns:
            monthly_chunks = self._chunk_columns(monthly_columns, self.monthly_columns_per_page)
            for col_idx, chunk in enumerate(monthly_chunks, start=1):
                for row_idx, (row_slice, hierarchy_slice) in enumerate(row_chunks, start=1):
                    rows = self._materialize_rows(row_slice, chunk, progress_map)
                    
                    # Calculate page number and total pages for this section
                    total_monthly_pages = len(monthly_chunks) * len(row_chunks)
                    current_page = (col_idx - 1) * len(row_chunks) + row_idx
                    
                    # Get month range from chunk (monthly mode)
                    month_start = chunk[0].get('month', 1) if chunk else 1
                    month_end = chunk[-1].get('month', month_start) if chunk else month_start
                    
                    # Use SHF for consistent header formatting (use months instead of weeks)
                    title = SHF.input_progress('PLANNED', current_page, total_monthly_pages, month_start, month_end)

                    pages.append(
                        {
                            "title": title,
                            "table_data": {
                                "headers": self._build_headers(chunk),
                                "rows": rows,
                            },
                            "col_widths": self._build_col_widths(len(chunk)),
                            "hierarchy_levels": hierarchy_slice,
                            "meta": {
                                "mode": "monthly",
                                "page_seq": page_seq,
                                "column_chunk": col_idx,
                                "row_chunk": row_idx,
                            },
                        }
                    )
                    page_seq += 1

        meta = {
            "weekly_columns": len(weekly_columns),
            "weekly_collapsed": False,
            "monthly_columns": len(monthly_columns),
            "rows": len(base_rows),
            "rows_per_page": self.max_rows_per_page,
        }

        return {"pages": pages, "meta": meta}

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
            "pekerjaan_id",
            "week_number",
            "planned_proportion",
            "week_start_date",
            "week_end_date",
        )

        for record in weekly_qs:
            key = (record.pekerjaan_id, record.week_number)
            try:
                progress_map[key] = Decimal(record.planned_proportion or 0)
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
            # Note: kode is no longer used - UNIFIED structure (no Kode column)
            uraian = row.get("uraian", "")
            volume_display = row.get("volume_display", "")
            unit = row.get("unit", "")

            if row.get("type") != "pekerjaan":
                volume_display = ""
                unit = ""

            # UNIFIED: 3 static columns (no Kode) - matches Kurva S and Gantt
            row_values = [uraian, volume_display, unit]

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
        # UNIFIED: 3 static columns (no Kode) - matches Kurva S and Gantt
        headers = ["Uraian Pekerjaan", "Volume", "Satuan"]
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

    def _chunk_rows(
        self, rows: Sequence[Dict[str, Any]], hierarchy: Dict[int, int], max_per_page: int
    ) -> List[Tuple[List[Dict[str, Any]], Dict[int, int]]]:
        if not max_per_page or max_per_page <= 0:
            return [(list(rows), dict(hierarchy))]
        chunks: List[Tuple[List[Dict[str, Any]], Dict[int, int]]] = []
        total = len(rows)
        for start in range(0, total, max_per_page):
            end = start + max_per_page
            row_slice = list(rows[start:end])
            hierarchy_slice = {
                idx - start: level for idx, level in hierarchy.items() if start <= idx < end
            }
            chunks.append((row_slice, hierarchy_slice))
        return chunks

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

    def _format_percent(self, value: Decimal | float | int, show_sign: bool = False) -> str:
        decimal_value = self._to_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formatted = f"{float(decimal_value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        if show_sign and decimal_value > 0:
            return f"+{formatted}%"
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

    # ------------------------------------------------------------------
    # Professional Report Methods (Laporan Tertulis)
    # ------------------------------------------------------------------

    def get_rekap_report_data(self) -> Dict[str, Any]:
        """
        Generate data for Laporan Rekapitulasi (Full Report).
        Separates Planned and Actual into distinct sections.
        
        Returns:
            Dict with 'planned_section', 'actual_section', 'kurva_s_data', 'summary'
        """
        import time
        start = time.time()
        step_times = {}
        
        step_start = time.time()
        weekly_tahapan = self._fetch_weekly_tahapan()
        step_times['fetch_tahapan'] = time.time() - step_start
        
        step_start = time.time()
        progress_map, progress_meta = self._build_progress_map()
        step_times['build_progress_map'] = time.time() - step_start
        
        step_start = time.time()
        actual_map = self._build_actual_progress_map()
        step_times['build_actual_map'] = time.time() - step_start

        self.project_start, self.project_end = self._resolve_project_dates(
            weekly_tahapan,
            progress_meta.get("earliest_start"),
            progress_meta.get("latest_end"),
        )

        step_start = time.time()
        weekly_columns = self._build_weekly_columns(
            weekly_tahapan, progress_meta.get("max_week_number", 0)
        )
        step_times['build_weekly_columns'] = time.time() - step_start
        
        step_start = time.time()
        monthly_columns = self._build_monthly_columns(weekly_columns)
        step_times['build_monthly_columns'] = time.time() - step_start

        step_start = time.time()
        base_rows, hierarchy = self._build_base_rows()
        step_times['build_base_rows'] = time.time() - step_start

        # Build planned section pages
        step_start = time.time()
        planned_pages = self._build_section_pages(
            base_rows, hierarchy, weekly_columns, progress_map, "PLANNED"
        )
        step_times['build_planned_pages'] = time.time() - step_start

        # Build actual section pages
        step_start = time.time()
        actual_pages = self._build_section_pages(
            base_rows, hierarchy, weekly_columns, actual_map, "ACTUAL"
        )
        step_times['build_actual_pages'] = time.time() - step_start

        # Calculate kurva S data
        step_start = time.time()
        kurva_s_data = self._calculate_kurva_s_data(progress_map, actual_map, base_rows, weekly_columns)
        step_times['calculate_kurva_s'] = time.time() - step_start

        # Calculate summary
        step_start = time.time()
        summary = self._calculate_project_summary(progress_map, actual_map, base_rows, weekly_columns)
        step_times['calculate_summary'] = time.time() - step_start

        # Log all timings
        total = time.time() - start
        print(f"[JadwalAdapter] get_rekap_report_data timing breakdown:")
        for step, duration in step_times.items():
            pct = (duration / total) * 100 if total > 0 else 0
            print(f"  - {step}: {duration:.2f}s ({pct:.1f}%)")
        print(f"[JadwalAdapter] Total: {total:.2f}s")

        return {
            "planned_pages": planned_pages,
            "actual_pages": actual_pages,
            "kurva_s_data": kurva_s_data,
            "summary": summary,
            "project_info": self._get_project_info(),
            "weekly_columns": weekly_columns,  # Added for Gantt week headers with dates
            "meta": {
                "total_weeks": len(weekly_columns),
                "total_months": len(monthly_columns),
                "total_pekerjaan": len([r for r in base_rows if r.get("type") == "pekerjaan"]),
            }
        }

    def get_monthly_comparison_data(self, month: int) -> Dict[str, Any]:
        """
        Generate data for Laporan Bulanan with comparison to previous month.
        
        Args:
            month: Target month number (1-based)
            
        Returns:
            Dict with 'current_month', 'previous_month', 'comparison', 'executive_summary'
        """
        weekly_tahapan = self._fetch_weekly_tahapan()
        progress_map, progress_meta = self._build_progress_map()
        actual_map = self._build_actual_progress_map()

        self.project_start, self.project_end = self._resolve_project_dates(
            weekly_tahapan,
            progress_meta.get("earliest_start"),
            progress_meta.get("latest_end"),
        )

        weekly_columns = self._build_weekly_columns(
            weekly_tahapan, progress_meta.get("max_week_number", 0)
        )
        base_rows, hierarchy = self._build_base_rows()

        # Calculate current month data (4 weeks per month)
        current_start_week = (month - 1) * 4 + 1
        current_end_week = month * 4
        current_data = self._calculate_period_data(
            progress_map, actual_map, base_rows, weekly_columns,
            current_start_week, current_end_week
        )

        # Calculate previous month data
        prev_month = month - 1
        previous_data = None
        if prev_month >= 1:
            prev_start_week = (prev_month - 1) * 4 + 1
            prev_end_week = prev_month * 4
            previous_data = self._calculate_period_data(
                progress_map, actual_map, base_rows, weekly_columns,
                prev_start_week, prev_end_week
            )

        # Calculate comparison
        comparison = self._calculate_comparison(current_data, previous_data)

        # Get week date ranges
        current_weeks = [col for col in weekly_columns if current_start_week <= col.get("week_number", 0) <= current_end_week]
        period_start = current_weeks[0].get("start_date") if current_weeks else None
        period_end = current_weeks[-1].get("end_date") if current_weeks else None

        # Calculate Kurva S data (cumulative) up to current month only
        # Chart will only show up to month * 4 weeks
        weekly_columns_for_chart = [
            col for col in weekly_columns
            if col.get("week_number", 0) <= current_end_week
        ]
        kurva_s_data = self._calculate_kurva_s_data(
            progress_map, actual_map, base_rows, weekly_columns_for_chart
        )
        
        # Total weeks in project (for table - render ALL weeks)
        total_project_weeks = len(weekly_columns)

        return {
            "month": month,
            "period": {
                "start_date": period_start,
                "end_date": period_end,
                "weeks": f"W{current_start_week}-W{current_end_week}"
            },
            "current_data": current_data,
            "previous_data": previous_data,
            "comparison": comparison,
            "executive_summary": self._build_executive_summary(current_data, previous_data, "monthly"),
            "project_info": self._get_project_info(),
            "hierarchy_progress": self._build_hierarchy_progress(
                base_rows, hierarchy, progress_map, actual_map,
                month, current_start_week, current_end_week
            ),
            "detail_table": self._build_period_detail_table(
                base_rows, hierarchy, progress_map, actual_map,
                current_start_week, current_end_week
            ),
            # Kurva S chart data (cumulative up to current month)
            "kurva_s_data": kurva_s_data,
            "cumulative_end_week": current_end_week,  # Chart stops here
            # ALL weekly columns for table (full project duration)
            "all_weekly_columns": weekly_columns,
            "total_project_weeks": total_project_weeks,
            # Filtered columns (for backward compatibility)
            "weekly_columns": weekly_columns_for_chart,
            # Row data
            "base_rows": base_rows,
            "hierarchy": hierarchy,
            # Progress maps for ALL weeks
            "planned_map": {f"{k[0]}-{k[1]}": float(v) for k, v in progress_map.items()},
            "actual_map": {f"{k[0]}-{k[1]}": float(v) for k, v in actual_map.items()},
        }

    def get_weekly_comparison_data(self, week: int) -> Dict[str, Any]:
        """
        Generate data for Laporan Mingguan with comparison to previous week.
        
        Args:
            week: Target week number (1-based)
            
        Returns:
            Dict with 'current_week', 'previous_week', 'comparison', 'executive_summary'
        """
        weekly_tahapan = self._fetch_weekly_tahapan()
        progress_map, progress_meta = self._build_progress_map()
        actual_map = self._build_actual_progress_map()

        self.project_start, self.project_end = self._resolve_project_dates(
            weekly_tahapan,
            progress_meta.get("earliest_start"),
            progress_meta.get("latest_end"),
        )

        weekly_columns = self._build_weekly_columns(
            weekly_tahapan, progress_meta.get("max_week_number", 0)
        )
        base_rows, hierarchy = self._build_base_rows()

        # Calculate current week data
        current_data = self._calculate_period_data(
            progress_map, actual_map, base_rows, weekly_columns, week, week
        )

        # Calculate previous week data
        previous_data = None
        if week > 1:
            previous_data = self._calculate_period_data(
                progress_map, actual_map, base_rows, weekly_columns, week - 1, week - 1
            )

        # Calculate comparison
        comparison = self._calculate_comparison(current_data, previous_data)

        # Get week date range
        week_col = next((col for col in weekly_columns if col.get("week_number") == week), None)
        period_start = week_col.get("start_date") if week_col else None
        period_end = week_col.get("end_date") if week_col else None
        
        # Build hierarchy progress for weekly report table
        hierarchy_progress = self._build_weekly_hierarchy_progress(
            base_rows, hierarchy, progress_map, actual_map, week
        )

        return {
            "week": week,
            "period": {
                "start_date": period_start,
                "end_date": period_end,
            },
            "current_data": current_data,
            "previous_data": previous_data,
            "comparison": comparison,
            "executive_summary": self._build_executive_summary(current_data, previous_data, "weekly"),
            "project_info": self._get_project_info(),
            "hierarchy_progress": hierarchy_progress,  # Added for PDF table rows
            "detail_table": self._build_period_detail_table(
                base_rows, hierarchy, progress_map, actual_map, week, week
            ),
        }

    def _build_actual_progress_map(self) -> Dict[Tuple[int, int], Decimal]:
        """Build progress map for actual progress (uses actual_proportion field)."""
        actual_map: Dict[Tuple[int, int], Decimal] = {}

        weekly_qs = PekerjaanProgressWeekly.objects.filter(project=self.project).only(
            "pekerjaan_id",
            "week_number",
            "actual_proportion",
        )

        for record in weekly_qs:
            key = (record.pekerjaan_id, record.week_number)
            try:
                actual_map[key] = Decimal(record.actual_proportion or 0)
            except InvalidOperation:
                actual_map[key] = Decimal("0")

        return actual_map

    def _build_section_pages(
        self,
        base_rows: List[Dict[str, Any]],
        hierarchy: Dict[int, int],
        weekly_columns: List[Dict[str, Any]],
        progress_map: Dict[Tuple[int, int], Decimal],
        section_title: str
    ) -> List[Dict[str, Any]]:
        """Build pages for a specific section (PLANNED or ACTUAL)."""
        pages: List[Dict[str, Any]] = []
        weekly_chunks = self._chunk_columns(weekly_columns, self.weekly_columns_per_page)
        row_chunks = self._chunk_rows(base_rows, hierarchy, self.max_rows_per_page)
        page_seq = 1

        for col_idx, chunk in enumerate(weekly_chunks, start=1):
            for row_idx, (row_slice, hierarchy_slice) in enumerate(row_chunks, start=1):
                rows = self._materialize_rows(row_slice, chunk, progress_map)
                
                # Calculate page number and total pages
                total_pages = len(weekly_chunks) * len(row_chunks)
                current_page = (col_idx - 1) * len(row_chunks) + row_idx
                
                # Get week range from chunk (key is 'week_number' not 'week')
                week_start = chunk[0].get('week_number', 1) if chunk else 1
                week_end = chunk[-1].get('week_number', week_start) if chunk else week_start
                
                # Use SHF for unified header format:
                # "Input Progress Planned - Halaman 1/3 (Minggu 1-18)"
                title = SHF.input_progress(section_title, current_page, total_pages, week_start, week_end)

                pages.append({
                    "title": title,
                    "section": section_title.lower(),
                    "table_data": {
                        "headers": self._build_headers(chunk),
                        "rows": rows,
                    },
                    "col_widths": self._build_col_widths(len(chunk)),
                    "hierarchy_levels": hierarchy_slice,
                    "meta": {
                        "page_seq": page_seq,
                        "column_chunk": col_idx,
                        "row_chunk": row_idx,
                    },
                })
                page_seq += 1

        return pages

    def _calculate_period_data(
        self,
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        base_rows: List[Dict[str, Any]],
        weekly_columns: List[Dict[str, Any]],
        start_week: int,
        end_week: int
    ) -> Dict[str, Any]:
        """
        Calculate aggregated data for a given period using BOBOT-WEIGHTED method.
        
        Progress is weighted by each pekerjaan's harga contribution to total project cost.
        This ensures pekerjaan with higher value contributes more to overall progress.
        """
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        
        # Calculate total harga for bobot calculation (before tax/markup)
        total_harga = Decimal("0")
        harga_map = {}  # pek_id -> harga
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                harga = self._get_pekerjaan_harga(pek_id)  # Already includes markup
                harga_map[pek_id] = harga
                total_harga += harga
        
        if total_harga == 0:
            total_harga = Decimal("1")  # Avoid division by zero
        
        # Calculate weighted progress
        weighted_planned_period = Decimal("0")
        weighted_actual_period = Decimal("0")
        weighted_planned_cumulative = Decimal("0")
        weighted_actual_cumulative = Decimal("0")

        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if not pek_id:
                continue
            
            # Calculate bobot (weight) for this pekerjaan
            harga = harga_map.get(pek_id, Decimal("0"))
            bobot = harga / total_harga  # Fraction of total project
            
            # Period progress (sum of weeks in range)
            period_planned = Decimal("0")
            period_actual = Decimal("0")
            for week in range(start_week, end_week + 1):
                period_planned += planned_map.get((pek_id, week), Decimal("0"))
                period_actual += actual_map.get((pek_id, week), Decimal("0"))
            
            # Cumulative progress (sum of all weeks up to end_week)
            cumul_planned = Decimal("0")
            cumul_actual = Decimal("0")
            for week in range(1, end_week + 1):
                cumul_planned += planned_map.get((pek_id, week), Decimal("0"))
                cumul_actual += actual_map.get((pek_id, week), Decimal("0"))
            
            # Apply bobot weighting
            weighted_planned_period += period_planned * bobot
            weighted_actual_period += period_actual * bobot
            weighted_planned_cumulative += cumul_planned * bobot
            weighted_actual_cumulative += cumul_actual * bobot

        return {
            "target_period": float(weighted_planned_period),
            "actual_period": float(weighted_actual_period),
            "cumulative_target": float(weighted_planned_cumulative),
            "cumulative_actual": float(weighted_actual_cumulative),
        }

    def _calculate_comparison(
        self,
        current_data: Dict[str, Any],
        previous_data: Dict[str, Any] | None
    ) -> Dict[str, Any]:
        """Calculate delta between current and previous period."""
        if not previous_data:
            return {
                "delta_target": current_data.get("target_period", 0),
                "delta_actual": current_data.get("actual_period", 0),
                "delta_cumulative": current_data.get("cumulative_actual", 0),
                "has_previous": False,
            }

        return {
            "delta_target": current_data.get("target_period", 0) - previous_data.get("target_period", 0),
            "delta_actual": current_data.get("actual_period", 0) - previous_data.get("actual_period", 0),
            "delta_cumulative": current_data.get("cumulative_actual", 0) - previous_data.get("cumulative_actual", 0),
            "has_previous": True,
        }

    def _build_executive_summary(
        self,
        current_data: Dict[str, Any],
        previous_data: Dict[str, Any] | None,
        mode: str
    ) -> Dict[str, Any]:
        """Build executive summary section for reports."""
        target = current_data.get("target_period", 0)
        actual = current_data.get("actual_period", 0)
        cumulative_target = current_data.get("cumulative_target", 0)
        cumulative_actual = current_data.get("cumulative_actual", 0)

        deviation = actual - target
        deviation_cumulative = cumulative_actual - cumulative_target

        # Determine status
        if deviation >= 0:
            status = "On Track" if deviation < 5 else "Ahead"
        else:
            status = "Behind" if deviation > -10 else "Critical"

        period_label = "Bulan Ini" if mode == "monthly" else "Minggu Ini"

        return {
            "target_period": round(target, 2),
            "actual_period": round(actual, 2),
            "deviation": round(deviation, 2),
            "cumulative_target": round(cumulative_target, 2),
            "cumulative_actual": round(cumulative_actual, 2),
            "deviation_cumulative": round(deviation_cumulative, 2),
            "status": status,
            "period_label": period_label,
        }

    def _build_hierarchy_progress(
        self,
        base_rows: List[Dict[str, Any]],
        hierarchy: Dict[int, int],
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        month: int,
        start_week: int,
        end_week: int
    ) -> List[Dict[str, Any]]:
        """
        Build hierarchical progress data for Rincian Progress table.
        
        Returns list of rows with:
        - type: 'klasifikasi', 'sub_klasifikasi', or 'pekerjaan'
        - level: hierarchy level for indentation
        - name: uraian pekerjaan
        - harga: total harga per pekerjaan
        - bobot: percentage of total project cost
        - progress_bulan_ini: weighted actual progress this month
        - progress_bulan_lalu: weighted actual progress previous month
        """
        volume_map = self._load_volume_map()
        
        # Calculate total harga for bobot
        total_harga = Decimal("0")
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                total_harga += self._get_pekerjaan_harga(pek_id)
        
        # Previous month weeks
        prev_month = month - 1
        prev_start_week = (prev_month - 1) * 4 + 1 if prev_month >= 1 else 0
        prev_end_week = prev_month * 4 if prev_month >= 1 else 0
        
        result = []
        
        # Track klasifikasi totals for aggregation
        klasifikasi_totals = {}  # idx -> {harga, bobot, progress_ini, progress_lalu}
        
        for idx, row in enumerate(base_rows):
            row_type = row.get("type")
            level = hierarchy.get(idx, 0)
            uraian = row.get("uraian", "")
            
            if row_type == "pekerjaan":
                pek_id = row.get("pekerjaan_id")
                
                # Get volume and harga_satuan
                from detail_project.models import VolumePekerjaan
                volume = Decimal("0")
                try:
                    vol = VolumePekerjaan.objects.get(pekerjaan_id=pek_id)
                    volume = self._to_decimal(vol.quantity)
                except VolumePekerjaan.DoesNotExist:
                    volume = Decimal("1")
                
                harga_dengan_markup = self._get_pekerjaan_harga(pek_id) if pek_id else Decimal("0")
                # Harga satuan = total / volume
                harga_satuan = harga_dengan_markup / volume if volume > 0 else Decimal("0")
                
                bobot = float(harga_dengan_markup / total_harga * 100) if total_harga > 0 else 0.0
                
                # Calculate actual progress this month (sum of weeks in this month)
                actual_ini = sum(
                    float(actual_map.get((pek_id, w), Decimal("0")))
                    for w in range(start_week, end_week + 1)
                ) if pek_id else 0.0
                
                # Calculate actual progress previous month
                actual_lalu = 0.0
                if prev_month >= 1 and pek_id:
                    actual_lalu = sum(
                        float(actual_map.get((pek_id, w), Decimal("0")))
                        for w in range(prev_start_week, prev_end_week + 1)
                    )
                
                # Weighted by bobot for total contribution
                progress_ini = actual_ini * bobot / 100 if bobot > 0 else 0.0
                progress_lalu = actual_lalu * bobot / 100 if bobot > 0 else 0.0
                
                result.append({
                    "type": "pekerjaan",
                    "level": level,
                    "name": uraian,
                    "pekerjaan_id": pek_id,  # Added for Portrait Kurva S progress lookup
                    "volume": float(volume),
                    "harga_satuan": float(harga_satuan),
                    "harga": float(harga_dengan_markup),
                    "bobot": round(bobot, 2),
                    "progress_bulan_ini": round(progress_ini, 2),
                    "progress_bulan_lalu": round(progress_lalu, 2),
                })
                
            else:
                # Klasifikasi or sub_klasifikasi - will be populated later from children
                result.append({
                    "type": row_type or "klasifikasi",
                    "level": level,
                    "name": uraian,
                    "harga": 0,
                    "bobot": 0,
                    "progress_bulan_ini": 0,
                    "progress_bulan_lalu": 0,
                })
        
        # Aggregate klasifikasi totals from children (bottom-up)
        # Simple approach: just leave klasifikasi with 0 for now
        # The PDF renderer will calculate if needed
        
        return result

    def _build_weekly_hierarchy_progress(
        self,
        base_rows: List[Dict[str, Any]],
        hierarchy: Dict[int, int],
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        week: int
    ) -> List[Dict[str, Any]]:
        """
        Build hierarchical progress data for Weekly Report table.
        Similar to _build_hierarchy_progress but with weekly field names.
        
        Returns list of rows with:
        - type: 'klasifikasi', 'sub_klasifikasi', or 'pekerjaan'
        - level: hierarchy level for indentation
        - name: uraian pekerjaan
        - volume: quantity
        - harga_satuan: unit price
        - harga: total harga per pekerjaan
        - bobot: percentage of total project cost
        - progress_minggu_ini: actual progress this week
        - progress_minggu_lalu: cumulative actual progress up to previous week
        """
        volume_map = self._load_volume_map()
        
        # Calculate total harga for bobot
        total_harga = Decimal("0")
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                total_harga += self._get_pekerjaan_harga(pek_id)
        
        result = []
        
        for idx, row in enumerate(base_rows):
            row_type = row.get("type")
            level = hierarchy.get(idx, 0)
            uraian = row.get("uraian", "")
            
            if row_type == "pekerjaan":
                pek_id = row.get("pekerjaan_id")
                
                # Get volume
                from detail_project.models import VolumePekerjaan
                volume = Decimal("0")
                try:
                    vol = VolumePekerjaan.objects.get(pekerjaan_id=pek_id)
                    volume = self._to_decimal(vol.quantity)
                except VolumePekerjaan.DoesNotExist:
                    volume = Decimal("1")
                
                harga_dengan_markup = self._get_pekerjaan_harga(pek_id) if pek_id else Decimal("0")
                # Harga satuan = total / volume
                harga_satuan = harga_dengan_markup / volume if volume > 0 else Decimal("0")
                
                bobot = float(harga_dengan_markup / total_harga * 100) if total_harga > 0 else 0.0
                
                # Calculate actual progress THIS WEEK ONLY (raw value)
                actual_ini = float(actual_map.get((pek_id, week), Decimal("0"))) if pek_id else 0.0
                
                # Calculate cumulative actual progress UP TO PREVIOUS WEEK (raw value)
                actual_lalu = 0.0
                if week > 1 and pek_id:
                    for w in range(1, week):
                        actual_lalu += float(actual_map.get((pek_id, w), Decimal("0")))
                
                # Weighted by bobot for total contribution (same as monthly)
                progress_ini = actual_ini * bobot / 100 if bobot > 0 else 0.0
                progress_lalu = actual_lalu * bobot / 100 if bobot > 0 else 0.0
                
                result.append({
                    "type": "pekerjaan",
                    "level": level,
                    "name": uraian,
                    "pekerjaan_id": pek_id,
                    "volume": float(volume),
                    "harga_satuan": float(harga_satuan),
                    "harga": float(harga_dengan_markup),
                    "bobot": round(bobot, 2),
                    "progress_minggu_ini": round(progress_ini, 2),  # Weighted by bobot
                    "progress_minggu_lalu": round(progress_lalu, 2),  # Weighted by bobot
                })
                
            else:
                # Klasifikasi or sub_klasifikasi - placeholders
                result.append({
                    "type": row_type or "klasifikasi",
                    "level": level,
                    "name": uraian,
                    "volume": 0,
                    "harga_satuan": 0,
                    "harga": 0,
                    "bobot": 0,
                    "progress_minggu_ini": 0,
                    "progress_minggu_lalu": 0,
                })
        
        return result


    def _build_period_detail_table(
        self,
        base_rows: List[Dict[str, Any]],
        hierarchy: Dict[int, int],
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        start_week: int,
        end_week: int
    ) -> Dict[str, Any]:
        """
        Build Tabel Progress Bulanan with Pekerjaan, Bobot, Target, Actual, Deviasi.
        
        Columns:
        1. No
        2. Uraian Pekerjaan
        3. Harga Pekerjaan
        4. Bobot (%)
        5. Target s/d Bln Ini (%) - Kumulatif
        6. Realisasi s/d Bln Ini (%) - Kumulatif
        7. Deviasi (%)
        8. Keterangan
        """
        volume_map = self._load_volume_map()
        
        # Calculate total harga for bobot calculation
        total_harga = Decimal("0")
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                total_harga += self._get_pekerjaan_harga(pek_id)

        headers = [
            "No",
            "Uraian Pekerjaan",
            "Harga Pekerjaan",
            "Bobot (%)",
            "Target s/d Bln Ini (%)",
            "Realisasi s/d Bln Ini (%)",
            "Deviasi (%)",
            "Keterangan",
        ]

        rows = []
        row_num = 0
        
        # Totals for footer
        total_target = Decimal("0")
        total_actual = Decimal("0")
        
        for idx, row in enumerate(base_rows):
            row_type = row.get("type")
            
            if row_type == "pekerjaan":
                row_num += 1
                pek_id = row.get("pekerjaan_id")
                harga = self._get_pekerjaan_harga(pek_id)
                bobot = (harga / total_harga * 100) if total_harga > 0 else Decimal("0")

                # Calculate cumulative progress (s/d bulan ini)
                cum_planned = sum(
                    planned_map.get((pek_id, w), Decimal("0"))
                    for w in range(1, end_week + 1)
                )
                cum_actual = sum(
                    actual_map.get((pek_id, w), Decimal("0"))
                    for w in range(1, end_week + 1)
                )
                
                # Weight by bobot for total calculation
                total_target += cum_planned * bobot / 100
                total_actual += cum_actual * bobot / 100
                
                # Deviasi
                deviasi = cum_actual - cum_planned

                rows.append({
                    "type": "pekerjaan",
                    "level": hierarchy.get(idx, 3),
                    "values": [
                        str(row_num),
                        row.get("uraian", ""),
                        self._format_number(harga, 0),
                        self._format_percent(bobot),
                        self._format_percent(cum_planned),
                        self._format_percent(cum_actual),
                        self._format_percent(deviasi, show_sign=True),
                        "",  # Keterangan (empty by default)
                    ]
                })
            else:
                rows.append({
                    "type": row_type,
                    "level": hierarchy.get(idx, 1),
                    "values": [
                        "",
                        row.get("uraian", ""),
                        "", "", "", "", "", ""
                    ]
                })
        
        # Add TOTAL row
        total_deviasi = total_actual - total_target
        rows.append({
            "type": "total",
            "level": 0,
            "values": [
                "",
                "TOTAL",
                self._format_number(total_harga, 0),
                "100.00%",
                self._format_percent(total_target),
                self._format_percent(total_actual),
                self._format_percent(total_deviasi, show_sign=True),
                "",
            ]
        })

        return {"headers": headers, "rows": rows}

    def _calculate_kurva_s_data(
        self,
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        base_rows: List[Dict[str, Any]],
        weekly_columns: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Calculate Kurva S data points using BOBOT-WEIGHTED method.
        
        Each pekerjaan's progress is weighted by its harga/total_harga.
        This ensures consistency with other progress calculations.
        """
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        
        # Calculate total harga and build harga map for bobot
        total_harga = Decimal("0")
        harga_map = {}  # pek_id -> harga
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                harga = self._get_pekerjaan_harga(pek_id)
                harga_map[pek_id] = harga
                total_harga += harga
        
        if total_harga == 0:
            total_harga = Decimal("1")  # Avoid division by zero
        
        # Calculate bobot for each pekerjaan
        bobot_map = {}  # pek_id -> bobot (fraction)
        for pek_id, harga in harga_map.items():
            bobot_map[pek_id] = harga / total_harga

        data = []
        cumulative_planned = Decimal("0")
        cumulative_actual = Decimal("0")

        for col in weekly_columns:
            week_number = col.get("week_number", 0)
            
            # Calculate weighted progress for this week
            week_planned_weighted = Decimal("0")
            week_actual_weighted = Decimal("0")

            for row in pekerjaan_rows:
                pek_id = row.get("pekerjaan_id")
                if pek_id:
                    bobot = bobot_map.get(pek_id, Decimal("0"))
                    week_planned = planned_map.get((pek_id, week_number), Decimal("0"))
                    week_actual = actual_map.get((pek_id, week_number), Decimal("0"))
                    
                    # Weight the progress by bobot
                    week_planned_weighted += week_planned * bobot
                    week_actual_weighted += week_actual * bobot

            cumulative_planned += week_planned_weighted
            cumulative_actual += week_actual_weighted

            data.append({
                "week": week_number,
                "label": col.get("label", f"W{week_number}"),
                "range": col.get("range", ""),
                "planned": float(cumulative_planned),
                "actual": float(cumulative_actual),
            })

        return data

    def _calculate_project_summary(
        self,
        planned_map: Dict[Tuple[int, int], Decimal],
        actual_map: Dict[Tuple[int, int], Decimal],
        base_rows: List[Dict[str, Any]],
        weekly_columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calculate overall project summary using BOBOT-WEIGHTED method.
        
        Consistent with other progress calculations - weighted by harga/total_harga.
        """
        pekerjaan_rows = [r for r in base_rows if r.get("type") == "pekerjaan"]
        total_weeks = len(weekly_columns)
        
        # Calculate total harga and bobot map
        total_harga = Decimal("0")
        harga_map = {}
        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if pek_id:
                harga = self._get_pekerjaan_harga(pek_id)
                harga_map[pek_id] = harga
                total_harga += harga
        
        if total_harga == 0:
            total_harga = Decimal("1")
        
        # Calculate weighted totals
        weighted_planned = Decimal("0")
        weighted_actual = Decimal("0")

        for row in pekerjaan_rows:
            pek_id = row.get("pekerjaan_id")
            if not pek_id:
                continue
            
            bobot = harga_map.get(pek_id, Decimal("0")) / total_harga
            
            for col in weekly_columns:
                week = col.get("week_number", 0)
                planned = planned_map.get((pek_id, week), Decimal("0"))
                actual = actual_map.get((pek_id, week), Decimal("0"))
                weighted_planned += planned * bobot
                weighted_actual += actual * bobot

        deviation = weighted_actual - weighted_planned

        return {
            "total_planned": float(weighted_planned),
            "total_actual": float(weighted_actual),
            "deviation": float(deviation),
            "total_weeks": total_weeks,
            "total_pekerjaan": len(pekerjaan_rows),
        }

    def _get_project_info(self) -> Dict[str, Any]:
        """Get project information for cover page and signature section."""
        return {
            "nama": getattr(self.project, "nama", "Proyek Tanpa Nama"),
            "lokasi": getattr(self.project, "lokasi", getattr(self.project, "lokasi_project", "-")),
            "anggaran": self._format_number(getattr(self.project, "anggaran_owner", 0), 0),
            "tanggal_mulai": self.project_start,
            "tanggal_selesai": self.project_end,
            "durasi_hari": getattr(self.project, "durasi_hari", 0),
            "sumber_dana": getattr(self.project, "sumber_dana", "-"),
            "nama_client": getattr(self.project, "nama_client", "-"),
            # Signature section fields
            "jabatan_client": getattr(self.project, "jabatan_client", "-"),
            "instansi_client": getattr(self.project, "instansi_client", "-"),
            "instansi_kontraktor": getattr(self.project, "instansi_kontraktor", "-"),
            "instansi_konsultan_pengawas": getattr(self.project, "instansi_konsultan_pengawas", "-"),
            # Signature names
            "nama_kontraktor": getattr(self.project, "nama_kontraktor", "-"),
            "nama_konsultan_pengawas": getattr(self.project, "nama_konsultan_pengawas", "-"),
        }

    def _build_rekap_harga_cache(self) -> Dict[int, Decimal]:
        """
        Build harga lookup cache from compute_rekap_for_project (canonical source).
        
        This ensures consistency with:
        - API /kurva-s-data/ endpoint
        - Rekap RAB calculations
        - All export reports
        
        Returns:
            Dict mapping pekerjaan_id -> total harga (G × volume, with markup)
        """
        cache: Dict[int, Decimal] = {}
        try:
            rekap_rows = compute_rekap_for_project(self.project)
            for row in rekap_rows:
                pek_id = row.get('pekerjaan_id')
                if pek_id:
                    total = Decimal(str(row.get('total', 0)))
                    cache[int(pek_id)] = total
        except Exception:
            pass  # Return empty cache on error
        return cache
    
    def _get_pekerjaan_harga(self, pekerjaan_id: int) -> Decimal:
        """
        Get total harga for a pekerjaan WITH profit/margin.
        
        Uses compute_rekap_for_project() as canonical source for consistency
        with API endpoints 
        and Rekap RAB calculations.
        
        Falls back to Decimal("0") if pekerjaan not found in rekap.
        """
        # Lazy load cache on first access
        if self._rekap_harga_cache is None:
            self._rekap_harga_cache = self._build_rekap_harga_cache()
        
        return self._rekap_harga_cache.get(int(pekerjaan_id), Decimal("0"))
