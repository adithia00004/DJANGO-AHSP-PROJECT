# detail_project/services.py
from typing import Dict, List, Optional, Set, Tuple
from django.db import transaction
from django.db.models import Sum, F as DJF, DecimalField, ExpressionWrapper
from decimal import Decimal
from collections import defaultdict
from django.db.models import Q
from .numeric import to_dp_str, DECIMAL_SPEC
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

from .models import (
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    DetailAHSPExpanded,
    HargaItemProject,
    ProjectPricing,
    ProjectParameter,
    TahapPelaksanaan,
    PekerjaanTahapan,
)

def invalidate_rekap_cache(project_or_id) -> None:
    """
    Hapus cache rekap untuk 1 project.
    Terima instance Project atau angka project_id.
    """
    try:
        pid = int(getattr(project_or_id, "id", project_or_id))
    except Exception:
        return
    cache.delete(f"rekap:{pid}:v1")
    cache.delete(f"rekap:{pid}:v2")  # tambahkan ini


# Import model referensi untuk cloning (aman bila app referensi belum siap saat makemigrations)
try:
    from referensi.models import AHSPReferensi, RincianReferensi  # type: ignore
except Exception:
    AHSPReferensi = None  # type: ignore
    RincianReferensi = None  # type: ignore


def _upsert_harga_item(project, kategori: str, kode_item: str, uraian: str, satuan: str | None):
    """
    Upsert master harga unik per proyek (tanpa mengubah harga_satuan).
    """
    obj, _created = HargaItemProject.objects.get_or_create(
        project=project, kode_item=kode_item,
        defaults=dict(kategori=kategori, uraian=uraian, satuan=satuan)
    )
    changed = False
    if obj.kategori != kategori:
        obj.kategori = kategori; changed = True
    if uraian and obj.uraian != uraian:
        obj.uraian = uraian; changed = True
    if (satuan or None) != obj.satuan:
        obj.satuan = satuan or None; changed = True
    if changed:
        obj.save(update_fields=["kategori", "uraian", "satuan", "updated_at"])
    return obj


def check_circular_dependency_pekerjaan(pekerjaan_id: int, ref_pekerjaan_id: int, project) -> tuple[bool, list[int]]:
    """
    Check apakah reference ke ref_pekerjaan_id akan create circular dependency.

    Returns:
        (is_circular, path):
            - is_circular: True jika circular dependency detected
            - path: List pekerjaan_id yang membentuk cycle (jika circular)

    Examples:
        >>> check_circular_dependency_pekerjaan(1, 2, project)
        (False, [])  # OK, tidak circular

        >>> # Pekerjaan 1 → 2 → 3 → 1 (circular!)
        >>> check_circular_dependency_pekerjaan(1, 2, project)
        (True, [1, 2, 3, 1])
    """
    # Self-reference adalah circular paling simple
    if pekerjaan_id == ref_pekerjaan_id:
        return (True, [pekerjaan_id, ref_pekerjaan_id])

    # BFS untuk detect cycle
    visited = set()
    path = [pekerjaan_id]
    queue = [(ref_pekerjaan_id, [pekerjaan_id, ref_pekerjaan_id])]

    while queue:
        current_id, current_path = queue.pop(0)

        if current_id in visited:
            continue
        visited.add(current_id)

        # Check apakah current_id references back ke pekerjaan_id
        refs = DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan_id=current_id,
            kategori='LAIN',
            ref_pekerjaan__isnull=False
        ).values_list('ref_pekerjaan_id', flat=True)

        for next_id in refs:
            if next_id == pekerjaan_id:
                # Found cycle!
                return (True, current_path + [pekerjaan_id])

            if next_id not in visited:
                queue.append((next_id, current_path + [next_id]))

    return (False, [])


def validate_bundle_reference(pekerjaan_id: int, ref_kind: str, ref_id: int, project) -> tuple[bool, str]:
    """
    Validate bundle reference untuk prevent circular dependency dan invalid reference.

    Returns:
        (is_valid, error_message):
            - is_valid: True jika valid
            - error_message: Pesan error jika tidak valid, empty string jika valid

    Validations:
        1. Self-reference (Pekerjaan tidak boleh reference ke diri sendiri)
        2. Circular dependency (A → B → C → A)
        3. Reference exists
        4. Reference dalam project yang sama (untuk ref_kind='job')
    """
    if ref_kind == 'job':
        ref_pekerjaan_id = ref_id

        # Validation 1: Self-reference
        if pekerjaan_id == ref_pekerjaan_id:
            return (False, "Pekerjaan tidak boleh mereferensi diri sendiri")

        # Validation 2: Check existence & same project
        try:
            ref_pekerjaan = Pekerjaan.objects.get(id=ref_pekerjaan_id, project=project)
        except Pekerjaan.DoesNotExist:
            return (False, f"Pekerjaan reference #{ref_pekerjaan_id} tidak ditemukan dalam project ini")

        # Validation 3: Circular dependency
        is_circular, cycle_path = check_circular_dependency_pekerjaan(pekerjaan_id, ref_pekerjaan_id, project)
        if is_circular:
            # Build readable error message
            pekerjaan_codes = []
            for pid in cycle_path:
                try:
                    p = Pekerjaan.objects.get(id=pid)
                    pekerjaan_codes.append(f"{p.snapshot_kode or pid}")
                except Pekerjaan.DoesNotExist:
                    pekerjaan_codes.append(str(pid))

            cycle_str = " → ".join(pekerjaan_codes)
            return (False, f"Circular dependency detected: {cycle_str}")

    elif ref_kind == 'ahsp':
        # AHSP reference validation (existing logic)
        try:
            if AHSPReferensi:
                AHSPReferensi.objects.get(id=ref_id)
        except Exception:
            return (False, f"AHSP reference #{ref_id} tidak ditemukan")

    return (True, "")


def expand_bundle_to_components(
    detail_data: dict,
    project,
    base_koef: Decimal = Decimal('1.0'),
    depth: int = 0,
    visited: Optional[Set[int]] = None
) -> List[dict]:
    """
    Expand bundle (LAIN dengan ref_pekerjaan) menjadi list komponen base (TK/BHN/ALT).

    Supports nested bundles (multi-level) dengan recursive expansion.
    Koefisien dikalikan secara hierarkis: Koef_Final = Koef_Bundle × Koef_Component.

    Args:
        detail_data: Dict dengan keys: kategori, kode, koefisien, ref_pekerjaan_id
        project: Project instance
        base_koef: Accumulated koefisien dari parent levels (untuk nested bundle)
        depth: Current expansion depth (untuk tracking & limit)
        visited: Set of pekerjaan_id untuk prevent infinite recursion

    Returns:
        List of dicts:
        [{
            'kategori': 'TK',
            'kode': 'TK.001',
            'uraian': 'Pekerja',
            'satuan': 'OH',
            'koefisien': Decimal('40.000000'),  # Already multiplied
            'harga_item': HargaItemProject instance,
            'depth': 1
        }, ...]

    Example:
        detail_data = {
            'kategori': 'LAIN',
            'kode': 'PG_A',
            'koefisien': Decimal('20.0'),
            'ref_pekerjaan_id': 123
        }

        # Pekerjaan 123 (PG_A) has:
        # - Bahan A (koef=1)
        # - Tenaga A (koef=2)

        Result:
        [
            {'kode': 'Bahan_A', 'koefisien': Decimal('20.0')},  # 1 × 20
            {'kode': 'Tenaga_A', 'koefisien': Decimal('40.0')}, # 2 × 20
        ]

    Raises:
        ValueError: Jika max depth exceeded atau circular dependency detected
    """
    MAX_DEPTH = 10

    # Check max depth
    if depth > MAX_DEPTH:
        raise ValueError(f"Maksimum kedalaman bundle expansion terlampaui (max {MAX_DEPTH})")

    # Initialize visited set
    if visited is None:
        visited = set()

    # Get bundle reference
    ref_pekerjaan_id = detail_data.get('ref_pekerjaan_id')
    if not ref_pekerjaan_id:
        # Not a bundle - shouldn't happen, but return empty to be safe
        logger.warning(f"[EXPAND_BUNDLE] Called for non-bundle detail (no ref_pekerjaan_id): {detail_data}")
        return []

    logger.info(f"[EXPAND_BUNDLE] Depth={depth}, Bundle='{detail_data.get('kode')}', Ref_Pekerjaan_ID={ref_pekerjaan_id}, Koef={detail_data.get('koefisien')}, Base_Koef={base_koef}")

    # Check circular dependency
    if ref_pekerjaan_id in visited:
        visited_codes = []
        for pid in visited:
            try:
                p = Pekerjaan.objects.get(id=pid)
                visited_codes.append(p.snapshot_kode or str(pid))
            except Pekerjaan.DoesNotExist:
                visited_codes.append(str(pid))

        cycle_str = " → ".join(visited_codes)
        logger.error(f"[EXPAND_BUNDLE] Circular dependency detected: {cycle_str}")
        raise ValueError(f"Circular dependency detected in bundle expansion: {cycle_str}")

    # Add to visited
    visited.add(ref_pekerjaan_id)

    # Get bundle koefisien
    bundle_koef = Decimal(str(detail_data.get('koefisien', '1.0')))

    # Fetch components dari ref_pekerjaan
    try:
        ref_pekerjaan = Pekerjaan.objects.get(id=ref_pekerjaan_id, project=project)
        logger.info(f"[EXPAND_BUNDLE] Found ref_pekerjaan: {ref_pekerjaan.snapshot_kode} (ID: {ref_pekerjaan.id})")
    except Pekerjaan.DoesNotExist:
        logger.error(f"[EXPAND_BUNDLE] Reference pekerjaan #{ref_pekerjaan_id} not found")
        raise ValueError(f"Reference pekerjaan #{ref_pekerjaan_id} tidak ditemukan")

    components = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=ref_pekerjaan
    ).select_related('harga_item').order_by('id')

    comp_count = components.count()
    logger.info(f"[EXPAND_BUNDLE] Found {comp_count} components in ref_pekerjaan")

    if comp_count == 0:
        logger.warning(f"[EXPAND_BUNDLE] No components found in ref_pekerjaan {ref_pekerjaan.snapshot_kode} - returning empty")
        # Remove from visited before returning
        visited.discard(ref_pekerjaan_id)
        return []

    result = []

    for comp in components:
        if comp.kategori == 'LAIN' and comp.ref_pekerjaan_id:
            # Nested bundle - recursive expansion
            nested_data = {
                'kategori': comp.kategori,
                'kode': comp.kode,
                'koefisien': comp.koefisien,
                'ref_pekerjaan_id': comp.ref_pekerjaan_id,
            }

            nested_components = expand_bundle_to_components(
                detail_data=nested_data,
                project=project,
                base_koef=base_koef * bundle_koef,
                depth=depth + 1,
                visited=visited.copy()  # Copy to avoid mutation in sibling branches
            )

            result.extend(nested_components)

        else:
            # Base component (TK/BHN/ALT) - add with multiplied koefisien
            final_koef = comp.koefisien * bundle_koef * base_koef

            result.append({
                'kategori': comp.kategori,
                'kode': comp.kode,
                'uraian': comp.uraian,
                'satuan': comp.satuan,
                'koefisien': final_koef,
                'harga_item': comp.harga_item,
                'depth': depth + 1
            })

    # Remove from visited after processing (for backtracking)
    visited.discard(ref_pekerjaan_id)

    logger.info(f"[EXPAND_BUNDLE] Expansion complete: {len(result)} base components returned")

    return result


def generate_custom_code(project) -> str:
    """
    Hasilkan kode otomatis untuk pekerjaan kustom: CUST-0001, CUST-0002, ...
    Unik 'secara praktis' per proyek (berbasis jumlah yang ada).
    """
    # Hitung yang sudah ada; +1 untuk nomor berikutnya
    n = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_CUSTOM).count() + 1
    return f"CUST-{n:04d}"


def _populate_expanded_from_raw(project, pekerjaan):
    """
    DUAL STORAGE HELPER: Populate DetailAHSPExpanded from DetailAHSPProject.

    For REF/REF_MODIFIED pekerjaan, items are direct input (TK/BHN/ALT), not bundles.
    We simply pass-through to expanded storage (no expansion needed).

    This is called after:
    - clone_ref_pekerjaan() creates DetailAHSPProject from referensi
    - User manually edits REF_MODIFIED details

    Args:
        project: Project instance
        pekerjaan: Pekerjaan instance
    """
    from .models import DetailAHSPProject, DetailAHSPExpanded

    logger.info(f"[POPULATE_EXPANDED] START - Project: {project.id}, Pekerjaan: {pekerjaan.id} ({pekerjaan.snapshot_kode})")

    # Delete old expanded data
    old_count = DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).count()
    DetailAHSPExpanded.objects.filter(project=project, pekerjaan=pekerjaan).delete()
    logger.info(f"[POPULATE_EXPANDED] Deleted {old_count} old expanded rows")

    # Read from raw storage
    raw_details = DetailAHSPProject.objects.filter(
        project=project,
        pekerjaan=pekerjaan
    ).select_related('harga_item').order_by('id')
    logger.info(f"[POPULATE_EXPANDED] Found {raw_details.count()} raw details to pass-through")

    # Pass-through to expanded storage (no bundle expansion for REF items)
    expanded_to_create = []
    for detail_obj in raw_details:
        expanded_to_create.append(DetailAHSPExpanded(
            project=project,
            pekerjaan=pekerjaan,
            source_detail=detail_obj,
            harga_item=detail_obj.harga_item,
            kategori=detail_obj.kategori,
            kode=detail_obj.kode,
            uraian=detail_obj.uraian,
            satuan=detail_obj.satuan,
            koefisien=detail_obj.koefisien,
            source_bundle_kode=None,  # Not from bundle
            expansion_depth=0,  # Direct input
        ))

    # Bulk create
    if expanded_to_create:
        DetailAHSPExpanded.objects.bulk_create(expanded_to_create, ignore_conflicts=True)
        logger.info(f"[POPULATE_EXPANDED] SUCCESS - Created {len(expanded_to_create)} expanded rows")
    else:
        logger.warning(f"[POPULATE_EXPANDED] No expanded rows to create")


@transaction.atomic
def clone_ref_pekerjaan(
    project,
    sub: SubKlasifikasi,
    ref_obj,
    source_type: str,
    ordering_index: int,
    auto_load_rincian: bool = True,
    *,
    override_uraian: Optional[str] = None,
    override_satuan: Optional[str] = None,
) -> Pekerjaan:
    """
    Clone snapshot identitas pekerjaan dari AHSP referensi dan,
    bila auto_load_rincian=True, clone semua rincian ke DetailAHSPProject.

    Penyesuaian:
    - source_type == ref          → snapshot_kode = <kode_ref>
    - source_type == ref_modified → snapshot_kode = "mod.X-<kode_ref>" (X bertambah per proyek)
      dan boleh override uraian/satuan dari parameter.
    """
    logger.info(f"[CLONE_REF_PKJ] START - Project: {project.id}, Source_Type: {source_type}, Auto_Load: {auto_load_rincian}")

    # Siapkan snapshot_kode sesuai mode
    rid = getattr(ref_obj, 'id', None)
    kode_ref   = getattr(ref_obj, 'kode_ahsp', None) or (f"REF-{rid}" if rid is not None else "REF")
    uraian_ref = getattr(ref_obj, 'nama_ahsp', None) or (f"AHSP {rid}" if rid is not None else "AHSP")
    satuan_ref = getattr(ref_obj, 'satuan', None)

    logger.info(f"[CLONE_REF_PKJ] Ref_Obj: ID={rid}, Kode={kode_ref}, Uraian={uraian_ref}")

    if source_type == Pekerjaan.SOURCE_REF_MOD:
        # nomor bertambah per proyek berdasarkan jumlah ref_modified yang sudah ada
        x = Pekerjaan.objects.filter(project=project, source_type=Pekerjaan.SOURCE_REF_MOD).count() + 1
        snap_kode = f"mod.{x}-{kode_ref}" if kode_ref else None
    else:
        snap_kode = kode_ref

    snap_uraian = override_uraian if (source_type == Pekerjaan.SOURCE_REF_MOD and override_uraian) else uraian_ref
    snap_satuan = override_satuan if (source_type == Pekerjaan.SOURCE_REF_MOD and override_satuan) else satuan_ref

    # Snapshot identitas pekerjaan dari referensi
    pkj = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=source_type,
        ref=ref_obj if AHSPReferensi is not None else None,
        snapshot_kode=snap_kode,
        snapshot_uraian=snap_uraian,
        snapshot_satuan=snap_satuan,
        auto_load_rincian=auto_load_rincian,
        ordering_index=ordering_index,
    )
    logger.info(f"[CLONE_REF_PKJ] Created Pekerjaan: ID={pkj.id}, Kode={snap_kode}, Source={source_type}")

    # Muat rincian dari referensi jika diminta
    if auto_load_rincian and RincianReferensi is not None:
        rincian_qs = RincianReferensi.objects.filter(ahsp=ref_obj).order_by('id')
        logger.info(f"[CLONE_REF_PKJ] Loading rincian: Found {rincian_qs.count()} rows")
        bulk_details: List[DetailAHSPProject] = []
        for rr in rincian_qs:
            # Kategori sinkron dengan app referensi: TK/BHN/ALT/LAIN
            kategori = rr.kategori
            kode = rr.kode_item
            uraian = rr.uraian_item
            satuan = rr.satuan_item
            koef = rr.koefisien

            hip = _upsert_harga_item(project, kategori, kode, uraian, satuan)
            bulk_details.append(DetailAHSPProject(
                project=project,
                pekerjaan=pkj,
                harga_item=hip,
                kategori=kategori,
                kode=kode,
                uraian=uraian,
                satuan=satuan,
                koefisien=koef,
            ))
        if bulk_details:
            DetailAHSPProject.objects.bulk_create(bulk_details, ignore_conflicts=True)
            logger.info(f"[CLONE_REF_PKJ] Created {len(bulk_details)} DetailAHSPProject rows")

            # DUAL STORAGE: Also populate DetailAHSPExpanded for REF/REF_MODIFIED
            # Items from referensi are direct input (TK/BHN/ALT), not bundles
            # So we pass-through to expanded storage
            logger.info(f"[CLONE_REF_PKJ] Calling _populate_expanded_from_raw for dual storage...")
            _populate_expanded_from_raw(project, pkj)
    logger.info(f"[CLONE_REF_PKJ] COMPLETE - Pekerjaan ID: {pkj.id}")
    return pkj

def expand_bundle_recursive(
    detail_dict: dict,
    base_koefisien: Decimal,
    project,
    depth: int = 0,
    visited: Optional[Set[tuple]] = None
) -> list[tuple]:
    """
    Recursively expand bundle item ke unit terkecil (TK/BHN/ALT).

    Args:
        detail_dict: Dict containing kategori, ref_ahsp_id, ref_pekerjaan_id, koefisien
        base_koefisien: Koefisien multiplier dari parent (accumulated)
        project: Project instance
        depth: Current recursion depth (untuk prevent infinite loop)
        visited: Set of visited (ref_kind, ref_id) untuk circular detection

    Returns:
        List of tuples: (kategori, kode, uraian, satuan, koefisien_total)

    Raises:
        ValueError: Jika circular dependency detected atau max depth exceeded
    """
    if visited is None:
        visited = set()

    MAX_DEPTH = 10  # Safety limit
    if depth > MAX_DEPTH:
        logger.error(
            f"Max recursion depth {MAX_DEPTH} exceeded during bundle expansion",
            extra={'detail': detail_dict, 'project_id': project.id}
        )
        raise ValueError(f"Maksimum kedalaman bundle ({MAX_DEPTH} level) terlampaui. Periksa struktur pekerjaan gabungan Anda.")

    hasil = []
    detail_koef = Decimal(str(detail_dict.get('koefisien', 0)))
    total_koef = base_koefisien * detail_koef

    # Case 1: Reference ke AHSPReferensi
    ref_ahsp_id = detail_dict.get('ref_ahsp_id')
    if ref_ahsp_id and RincianReferensi:
        bundle_key = ('ahsp', ref_ahsp_id)

        # Circular dependency check
        if bundle_key in visited:
            logger.error(
                f"Circular dependency detected: AHSP #{ref_ahsp_id}",
                extra={'visited': list(visited), 'project_id': project.id}
            )
            raise ValueError(f"Circular dependency detected pada AHSP Referensi #{ref_ahsp_id}")

        visited.add(bundle_key)

        try:
            # Get rincian dari AHSP Referensi
            ref_items = RincianReferensi.objects.filter(ahsp_id=ref_ahsp_id).values(
                'kategori', 'kode_item', 'uraian_item', 'satuan_item', 'koefisien'
            )

            for ref_item in ref_items:
                if ref_item['kategori'] in ['TK', 'BHN', 'ALT']:
                    # Base case: sudah level terkecil
                    ref_koef = Decimal(str(ref_item['koefisien']))
                    final_koef = total_koef * ref_koef
                    hasil.append((
                        ref_item['kategori'],
                        ref_item['kode_item'],
                        ref_item['uraian_item'],
                        ref_item['satuan_item'],
                        final_koef
                    ))
                # Note: RincianReferensi biasanya tidak memiliki kategori LAIN yang recursive
        finally:
            visited.remove(bundle_key)

    # Case 2: Reference ke Pekerjaan dalam project (NEW!)
    ref_pekerjaan_id = detail_dict.get('ref_pekerjaan_id')
    if ref_pekerjaan_id:
        bundle_key = ('job', ref_pekerjaan_id)

        # Circular dependency check
        if bundle_key in visited:
            # Get pekerjaan codes for better error message
            try:
                pkj = Pekerjaan.objects.get(id=ref_pekerjaan_id)
                pkj_code = pkj.snapshot_kode or f"#{ref_pekerjaan_id}"
            except Pekerjaan.DoesNotExist:
                pkj_code = f"#{ref_pekerjaan_id}"

            logger.error(
                f"Circular dependency detected: Pekerjaan {pkj_code}",
                extra={'visited': list(visited), 'project_id': project.id}
            )
            raise ValueError(f"Circular dependency detected pada Pekerjaan {pkj_code}")

        visited.add(bundle_key)

        try:
            # Get detail dari Pekerjaan yang di-reference
            ref_details = DetailAHSPProject.objects.filter(
                project=project,
                pekerjaan_id=ref_pekerjaan_id
            ).values('kategori', 'kode', 'uraian', 'satuan', 'koefisien', 'ref_ahsp_id', 'ref_pekerjaan_id')

            for ref_detail in ref_details:
                if ref_detail['kategori'] in ['TK', 'BHN', 'ALT']:
                    # Base case: sudah level terkecil
                    ref_koef = Decimal(str(ref_detail['koefisien']))
                    final_koef = total_koef * ref_koef
                    hasil.append((
                        ref_detail['kategori'],
                        ref_detail['kode'],
                        ref_detail['uraian'],
                        ref_detail['satuan'],
                        final_koef
                    ))
                elif ref_detail['kategori'] == 'LAIN':
                    # Recursive case: expand lagi
                    if ref_detail['ref_ahsp_id'] or ref_detail['ref_pekerjaan_id']:
                        sub_items = expand_bundle_recursive(
                            ref_detail,
                            total_koef,
                            project,
                            depth + 1,
                            visited
                        )
                        hasil.extend(sub_items)
        finally:
            visited.remove(bundle_key)

    return hasil


def _get_markup_percent(project) -> Decimal:
    # ⬇️ Tambahkan import lokal ini
    from .models import ProjectPricing
    obj = ProjectPricing.objects.filter(project=project).first()
    if obj and obj.markup_percent is not None:
        return Decimal(str(obj.markup_percent))
    return Decimal("0.00")

def compute_rekap_for_project(project):
    key = f"rekap:{project.id}:v2"   # bump cache version
    data = cache.get(key)
    if data is not None:
        return data
    """
    Hitung komponen biaya per pekerjaan (pakai override Profit/Margin per-pekerjaan jika ada):
      A = Σ(TK), B = Σ(BHN), C = Σ(ALT), LAIN = Σ(LAIN)
      D = A+B+C  (kompat historis)
      E_base = A+B+C+LAIN
      F = E_base × markup_eff   (markup_eff = override% jika ada, else project Profit/Margin %)
      G = E_base + F            (HSP/unit sesudah markup)
      total = G × volume
    Nilai kompat:
      E (lama) diisi = F (margin) agar test lama tetap lolos,
      HSP = E_base (pra-markup) untuk konsistensi dengan halaman Volume & test.
    """
    # --- Ambil Profit/Margin default proyek (fallback 10.00)
    proj_markup = Decimal("0")
    try:
        pp = ProjectPricing.objects.filter(project=project).first()
        if pp and pp.markup_percent is not None:
            proj_markup = Decimal(pp.markup_percent)
    except Exception:
        pass

    # --- Agregasi nilai per kategori
    # NEW: Read from DetailAHSPExpanded (dual storage - already expanded!)
    price = DJF('harga_item__harga_satuan')
    coef  = DJF('koefisien')  # Already multiplied koef from expansion
    nilai = ExpressionWrapper(coef * price, output_field=DecimalField(max_digits=20, decimal_places=2))

    base = (DetailAHSPExpanded.objects
            .filter(project=project)
            .values('pekerjaan_id', 'kategori')
            .annotate(jumlah=Sum(nilai)))

    kategori_keys = ['TK', 'BHN', 'ALT', 'LAIN']
    agg: Dict[int, Dict[str, float]] = {}
    for row in base:
        pkj_id = row['pekerjaan_id']
        kat    = row['kategori']
        if kat not in kategori_keys:
            continue
        agg.setdefault(pkj_id, {k: 0.0 for k in kategori_keys})
        agg[pkj_id][kat] = float(row['jumlah'] or 0.0)

    # --- Volume map
    vol_map = dict(VolumePekerjaan.objects
                   .filter(project=project)
                   .values_list('pekerjaan_id', 'quantity'))

    # --- Iterasi pekerjaan sekalian baca override
    result = []
    for p in (Pekerjaan.objects
              .filter(project=project)
              .order_by('ordering_index', 'id')
              .values('id', 'snapshot_kode', 'snapshot_uraian', 'snapshot_satuan', 'markup_override_percent')):
        pkj_id   = p['id']
        A        = agg.get(pkj_id, {}).get('TK', 0.0)  or 0.0
        B        = agg.get(pkj_id, {}).get('BHN', 0.0) or 0.0
        C        = agg.get(pkj_id, {}).get('ALT', 0.0) or 0.0
        LAIN     = agg.get(pkj_id, {}).get('LAIN', 0.0) or 0.0

        D        = A + B + C
        E_base   = D + LAIN

        # --- effective markup: override jika ada, else project
        ov = p.get('markup_override_percent', None)
        mp = float(ov if ov is not None else proj_markup)   # persen (mis. 12.5)
        mp_frac = mp / 100.0

        F      = E_base * mp_frac
        G      = E_base + F
        volume = float(vol_map.get(pkj_id) or 0.0)
        total  = float(G) * volume

        result.append(dict(
            pekerjaan_id = pkj_id,
            kode         = p['snapshot_kode'],
            uraian       = p['snapshot_uraian'],
            satuan       = p['snapshot_satuan'],

            A=A, B=B, C=C, D=D,
            LAIN=LAIN,
            E_base=E_base,

            E=F,          # margin (kompat lama)
            F=F,          # margin eksplisit
            G=G,          # unit price sesudah markup

            HSP=E_base,       # ★ unit price pra-markup (dipakai beberapa test/halaman)
            unit_price=E_base,# alias aman untuk FE

            markup_eff=mp,    # persen efektif
            volume=volume,
            total=total,      # = G * volume
        ))
    cache.set(key, result, 300)  # 5 menit (atau sesuai kebutuhan)
    return result


def compute_kebutuhan_items(
    project, 
    mode='all', 
    tahapan_id=None, 
    filters=None
):
    """
    Compute rekap kebutuhan dengan support split volume dan filtering.
    
    Args:
        project: Project instance
        mode: str - 'all' | 'tahapan'
            - 'all': Semua pekerjaan (default)
            - 'tahapan': Filter berdasarkan tahapan tertentu
        tahapan_id: int - ID tahapan (required jika mode='tahapan')
        filters: dict - Additional filters:
            - klasifikasi_ids: list[int] - Filter by klasifikasi
            - sub_klasifikasi_ids: list[int] - Filter by sub-klasifikasi
            - kategori_items: list[str] - Filter by kategori item (TK/BHN/ALT/LAIN)
    
    Returns:
        list of dict: [{kategori, kode, uraian, satuan, quantity, metadata}, ...]
        
    Examples:
        # Semua pekerjaan
        >>> rows = compute_kebutuhan_items(project)
        
        # Tahapan tertentu
        >>> rows = compute_kebutuhan_items(project, mode='tahapan', tahapan_id=1)
        
        # Dengan filter klasifikasi
        >>> rows = compute_kebutuhan_items(
        ...     project, 
        ...     filters={'klasifikasi_ids': [1, 2]}
        ... )
        
        # Tahapan + filter kategori
        >>> rows = compute_kebutuhan_items(
        ...     project,
        ...     mode='tahapan',
        ...     tahapan_id=1,
        ...     filters={'kategori_items': ['TK', 'BHN']}
        ... )
    """
    # ========================================================================
    # STEP 1: Determine scope - pekerjaan mana yang akan di-aggregate
    # ========================================================================
    
    if mode == 'tahapan' and tahapan_id:
        # Mode tahapan: ambil pekerjaan dari tahapan tertentu dengan proporsi
        pt_qs = PekerjaanTahapan.objects.filter(
            tahapan_id=tahapan_id
        ).select_related('pekerjaan', 'tahapan')
        
        # Build dict: pekerjaan_id -> proporsi (dalam bentuk Decimal 0-1)
        pekerjaan_proporsi = {
            pt.pekerjaan_id: pt.proporsi_volume / Decimal('100')
            for pt in pt_qs
        }
        pekerjaan_ids = list(pekerjaan_proporsi.keys())
        
    else:
        # Mode 'all': semua pekerjaan dengan proporsi 100%
        pekerjaan_ids = list(
            Pekerjaan.objects.filter(project=project).values_list('id', flat=True)
        )
        pekerjaan_proporsi = {pk: Decimal('1.0') for pk in pekerjaan_ids}
    
    # ========================================================================
    # STEP 2: Apply additional filters (klasifikasi, sub-klasifikasi)
    # ========================================================================
    
    if filters:
        queryset = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
        
        # Filter by klasifikasi
        if filters.get('klasifikasi_ids'):
            queryset = queryset.filter(
                sub_klasifikasi__klasifikasi_id__in=filters['klasifikasi_ids']
            )
        
        # Filter by sub-klasifikasi
        if filters.get('sub_klasifikasi_ids'):
            queryset = queryset.filter(
                sub_klasifikasi_id__in=filters['sub_klasifikasi_ids']
            )
        
        # Update pekerjaan_ids setelah filter
        pekerjaan_ids = list(queryset.values_list('id', flat=True))
    
    # Jika tidak ada pekerjaan dalam scope, return empty
    if not pekerjaan_ids:
        return []
    
    # ========================================================================
    # STEP 3: Get volume map untuk semua pekerjaan dalam scope
    # ========================================================================
    
    vol_map = dict(
        VolumePekerjaan.objects
        .filter(project=project, pekerjaan_id__in=pekerjaan_ids)
        .values_list('pekerjaan_id', 'quantity')
    )
    
    # ========================================================================
    # STEP 4: Aggregate items dengan proporsi volume
    # ========================================================================
    
    # Dictionary untuk agregasi: key = (kategori, kode, uraian, satuan)
    aggregated = defaultdict(Decimal)
    
    # Get all detail items untuk pekerjaan dalam scope
    # NEW: Read from DetailAHSPExpanded (dual storage - already expanded!)
    details = DetailAHSPExpanded.objects.filter(
        project=project,
        pekerjaan_id__in=pekerjaan_ids
    ).select_related('harga_item').values(
        'pekerjaan_id',
        'kategori',
        'kode',
        'uraian',
        'satuan',
        'koefisien',  # Already multiplied koefisien from expansion!
        'source_bundle_kode',  # For tracking
        'expansion_depth'  # For debugging
    )

    # Process each detail item
    for detail in details:
        pekerjaan_id = detail['pekerjaan_id']

        # Get volume dan proporsi
        volume_total = Decimal(str(vol_map.get(pekerjaan_id, 0) or 0))
        proporsi = pekerjaan_proporsi.get(pekerjaan_id, Decimal('1.0'))

        # Volume efektif dengan proporsi
        volume_efektif = volume_total * proporsi

        if volume_efektif == 0:
            continue

        kategori = detail['kategori']
        koefisien = Decimal(str(detail['koefisien'] or 0))  # Already expanded koef!

        # No expansion needed - DetailAHSPExpanded already has expanded components!
        # Just aggregate directly
        key = (
            kategori,
            detail['kode'],
            detail['uraian'],
            detail['satuan']
        )
        qty = koefisien * volume_efektif
        aggregated[key] += qty
    
    # ========================================================================
    # STEP 5: Apply kategori filter (jika ada)
    # ========================================================================
    
    if filters and filters.get('kategori_items'):
        allowed_kat = set(filters['kategori_items'])
        aggregated = {
            k: v for k, v in aggregated.items() 
            if k[0] in allowed_kat
        }
    
    # ========================================================================
    # STEP 6: Format output
    # ========================================================================
    
    rows = []
    for (kategori, kode, uraian, satuan), quantity in aggregated.items():
        # Format quantity dengan 6 decimal places, remove trailing zeros
        qty_str = f"{quantity:.6f}".rstrip('0').rstrip('.')
        
        rows.append({
            'kategori': kategori,
            'kode': kode or '-',
            'uraian': uraian or '-',
            'satuan': satuan or '-',
            'quantity': qty_str,  # String untuk display
            'quantity_decimal': quantity,  # Decimal untuk calculation
        })
    
    # ========================================================================
    # STEP 7: Sort output
    # ========================================================================
    
    # Sort by kategori (TK -> BHN -> ALT -> LAIN), then by kode
    kategori_order = {'TK': 1, 'BHN': 2, 'ALT': 3, 'LAIN': 4}
    rows.sort(key=lambda x: (
        kategori_order.get(x['kategori'], 99), 
        x['kode'] or '', 
        x['uraian'] or ''
    ))
    
    return rows



def get_tahapan_summary(project):
    """
    Get summary info untuk semua tahapan dalam project.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Summary info per tahapan
        
    Example:
        [
            {
                'tahapan_id': 1,
                'nama': 'Tahap 1: Persiapan',
                'urutan': 1,
                'jumlah_pekerjaan': 3,
                'total_assigned_proportion': 300.00,  # 3 pekerjaan @ 100%
                'tanggal_mulai': '2025-01-01',
                'tanggal_selesai': '2025-01-15'
            },
            ...
        ]
    """
    tahapan_list = TahapPelaksanaan.objects.filter(
        project=project
    ).prefetch_related('pekerjaan_items').order_by('urutan', 'id')
    
    result = []
    for tahap in tahapan_list:
        # Count pekerjaan dan total proporsi
        assignments = tahap.pekerjaan_items.all()
        jumlah_pekerjaan = assignments.values('pekerjaan').distinct().count()
        total_proporsi = sum(a.proporsi_volume for a in assignments)
        
        result.append({
            'tahapan_id': tahap.id,
            'nama': tahap.nama,
            'urutan': tahap.urutan,
            'deskripsi': tahap.deskripsi,
            'jumlah_pekerjaan': jumlah_pekerjaan,
            'total_assigned_proportion': float(total_proporsi),
            'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
            'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
            'created_at': tahap.created_at.isoformat() if tahap.created_at else None,
            'is_auto_generated': tahap.is_auto_generated,
            'generation_mode': tahap.generation_mode,
        })
    
    return result


def get_unassigned_pekerjaan(project):
    """
    Get list pekerjaan yang belum fully assigned ke tahapan.
    
    Args:
        project: Project instance
    
    Returns:
        list of dict: Pekerjaan yang belum/partial assigned
        
    Example:
        [
            {
                'pekerjaan_id': 5,
                'kode': '1.1.1',
                'uraian': 'Galian Tanah',
                'assigned_proportion': 60.00,
                'unassigned_proportion': 40.00,
                'status': 'partial'  # 'unassigned' | 'partial'
            },
            ...
        ]
    """
    from django.db.models import Sum, F
    
    # Get all pekerjaan dengan total assigned proportion
    pekerjaan_qs = Pekerjaan.objects.filter(
        project=project
    ).annotate(
        total_assigned=Sum('tahapan_assignments__proporsi_volume')
    ).order_by('ordering_index', 'id')
    
    result = []
    for pkj in pekerjaan_qs:
        assigned = float(pkj.total_assigned or 0)
        unassigned = 100.0 - assigned
        
        # Skip jika fully assigned
        if abs(unassigned) < 0.01:
            continue
        
        # Determine status
        if assigned < 0.01:
            status = 'unassigned'
        else:
            status = 'partial'
        
        result.append({
            'pekerjaan_id': pkj.id,
            'kode': pkj.snapshot_kode,
            'uraian': pkj.snapshot_uraian,
            'assigned_proportion': assigned,
            'unassigned_proportion': unassigned,
            'status': status,
            'klasifikasi': (pkj.sub_klasifikasi.klasifikasi.name 
                        if pkj.sub_klasifikasi and pkj.sub_klasifikasi.klasifikasi 
                        else None),
            'sub_klasifikasi': (pkj.sub_klasifikasi.name
                            if pkj.sub_klasifikasi
                            else None),
        })

    return result


# ==============================================================================
# Deep Copy Service - FASE 3.1 (Enhanced with Error Handling)
# ==============================================================================

import logging
from .exceptions import (
    DeepCopyValidationError,
    DeepCopyBusinessError,
    DeepCopyDatabaseError,
    DeepCopySystemError,
    classify_database_error,
    classify_system_error,
)

logger = logging.getLogger(__name__)


class DeepCopyService:
    """
    Service for deep copying projects with all related data.

    Implements a 12-step dependency-ordered copy process with ID mapping
    to handle foreign key relationships correctly.

    Enhanced Features (FASE 3.1.1):
        - Comprehensive input validation
        - Skip tracking for orphaned data
        - Warnings collection for user feedback
        - Detailed error classification
        - Structured logging

    Usage:
        service = DeepCopyService(source_project)
        new_project = service.copy(
            new_owner=request.user,
            new_name="Project Copy",
            new_tanggal_mulai=date(2025, 1, 1),
            copy_jadwal=True
        )

        # Check warnings
        warnings = service.get_warnings()
        skipped = service.get_skipped_items()

    Architecture:
        1. Uses transaction.atomic for data integrity
        2. Maintains ID mappings to remap FKs correctly
        3. Follows dependency order to avoid FK constraint violations
        4. Validates all copied data before saving
        5. Tracks skipped items and generates warnings
    """

    def __init__(self, source_project):
        """
        Initialize the service with source project.

        Args:
            source_project: The project to copy from

        Raises:
            DeepCopyValidationError: If source_project is invalid
            DeepCopyBusinessError: If project is too large (warning only)
        """
        # Validate source project exists
        if not source_project:
            raise DeepCopyValidationError(
                code=3002,
                message="Source project is None",
                details={"project": None}
            )

        if not source_project.id:
            raise DeepCopyValidationError(
                code=3002,
                message="Source project is not saved (no ID)",
                details={"project": str(source_project)}
            )

        self.source = source_project

        # Validate project size and log warning for large projects
        from .models import Pekerjaan
        pekerjaan_count = Pekerjaan.objects.filter(project=source_project).count()

        if pekerjaan_count > 1000:
            logger.warning(
                f"Large project copy initiated: {pekerjaan_count} pekerjaan",
                extra={
                    'project_id': source_project.id,
                    'pekerjaan_count': pekerjaan_count,
                    'source': 'DeepCopyService.__init__'
                }
            )
            # Don't block, just warn - business decides if this is acceptable

        # Initialize tracking structures
        self.warnings = []
        self.skipped_items = {
            'subklasifikasi': [],
            'pekerjaan': [],
            'volume': [],
            'ahsp_template': [],
        }

        # ID mapping dictionaries for FK remapping
        # Format: {old_id: new_id}
        self.mappings = {
            'project': {},
            'pricing': {},
            'parameter': {},
            'klasifikasi': {},
            'subklasifikasi': {},
            'pekerjaan': {},
            'volume': {},
            'harga_item': {},
            'ahsp_template': {},
            'rincian_ahsp': {},
            'tahapan': {},
            'jadwal': {},
        }

        self.stats = {
            'klasifikasi_copied': 0,
            'subklasifikasi_copied': 0,
            'pekerjaan_copied': 0,
            'volume_copied': 0,
            'harga_item_copied': 0,
            'ahsp_template_copied': 0,
            'rincian_ahsp_copied': 0,
            'parameter_copied': 0,
            'tahapan_copied': 0,
            'jadwal_copied': 0,
        }

    @transaction.atomic
    def copy(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai=None,
        copy_jadwal=True
    ):
        """
        Perform deep copy of project with all related data (Enhanced).

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project (optional)
            copy_jadwal: Whether to copy schedule data (default: True)

        Returns:
            The newly created project instance

        Raises:
            DeepCopyValidationError: If input validation fails
            DeepCopyBusinessError: If business rules violated
            DeepCopyDatabaseError: If database operation fails
            DeepCopySystemError: If system resource error occurs
        """
        from dashboard.models import Project
        from django.db import IntegrityError, OperationalError, ProgrammingError
        import re

        # ===== INPUT VALIDATION =====

        # Validate new_name is not empty
        if not new_name or not new_name.strip():
            raise DeepCopyValidationError(
                code=1001,
                message="Project name is empty",
                details={'new_name': new_name}
            )

        new_name = new_name.strip()

        # Validate name length
        if len(new_name) > 200:
            raise DeepCopyValidationError(
                code=1004,
                message=f"Project name too long: {len(new_name)} characters",
                details={'length': len(new_name), 'max': 200, 'name': new_name}
            )

        # XSS prevention - check for HTML tags
        if re.search(r'[<>]', new_name):
            raise DeepCopyValidationError(
                code=1007,
                message=f"Project name contains invalid characters: {new_name}",
                details={'name': new_name, 'invalid_chars': '<>'}
            )

        # Validate date range if provided
        if new_tanggal_mulai:
            if new_tanggal_mulai.year > 2100 or new_tanggal_mulai.year < 1900:
                raise DeepCopyValidationError(
                    code=1003,
                    message=f"Invalid date range: {new_tanggal_mulai}",
                    details={'date': str(new_tanggal_mulai), 'valid_range': '1900-2100'}
                )

        # ===== BUSINESS RULE VALIDATION =====

        # Check for duplicate project name
        if Project.objects.filter(owner=new_owner, nama=new_name).exists():
            raise DeepCopyBusinessError(
                code=3001,
                message=f"Project with name '{new_name}' already exists for user {new_owner.id}",
                details={
                    'owner_id': new_owner.id,
                    'owner_username': new_owner.username,
                    'project_name': new_name
                }
            )

        # Log copy initiation
        logger.info(
            f"Starting deep copy of project {self.source.id}",
            extra={
                'source_project_id': self.source.id,
                'source_project_name': self.source.nama,
                'new_owner_id': new_owner.id,
                'new_project_name': new_name,
                'copy_jadwal': copy_jadwal
            }
        )

        # ===== EXECUTE COPY WITH ERROR HANDLING =====

        try:
            # Step 1: Copy Project
            new_project = self._copy_project(new_owner, new_name, new_tanggal_mulai)

            # Step 2: Copy ProjectPricing
            self._copy_project_pricing(new_project)

            # Step 3: Copy ProjectParameter
            self._copy_project_parameters(new_project)

            # Step 4: Copy Klasifikasi
            self._copy_klasifikasi(new_project)

            # Step 5: Copy SubKlasifikasi
            self._copy_subklasifikasi(new_project)

            # Step 6: Copy Pekerjaan
            self._copy_pekerjaan(new_project)

            # Step 7: Copy VolumePekerjaan
            self._copy_volume_pekerjaan(new_project)

            # Step 8: Copy HargaItem
            self._copy_harga_item(new_project)

            # Step 9: Copy AhspTemplate (using existing model)
            self._copy_ahsp_template(new_project)

            # Step 10: Copy RincianAhsp (using DetailAHSPProject model)
            self._copy_rincian_ahsp(new_project)

            # Step 11: Copy Tahapan (if copy_jadwal=True)
            if copy_jadwal:
                self._copy_tahapan(new_project)

                # Step 12: Copy JadwalPekerjaan (if copy_jadwal=True)
                self._copy_jadwal_pekerjaan(new_project)

            # Check if any items were skipped and generate warnings
            if any(self.skipped_items.values()):
                skipped_summary = {k: len(v) for k, v in self.skipped_items.items() if v}
                logger.warning(
                    f"Some items were skipped during copy",
                    extra={
                        'source_project_id': self.source.id,
                        'new_project_id': new_project.id,
                        'skipped_summary': skipped_summary
                    }
                )

                self.warnings.append({
                    'code': 3005,
                    'message': f"Beberapa data tidak lengkap: {', '.join([f'{k}: {v}' for k, v in skipped_summary.items()])}",
                    'details': skipped_summary
                })

            # Log success
            stats = self.get_stats()
            logger.info(
                f"Deep copy completed successfully",
                extra={
                    'source_project_id': self.source.id,
                    'new_project_id': new_project.id,
                    'new_project_name': new_project.nama,
                    'stats': stats,
                    'warnings_count': len(self.warnings)
                }
            )

            return new_project

        except (IntegrityError, OperationalError, ProgrammingError) as e:
            # Classify database errors
            logger.error(
                f"Database error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise classify_database_error(e)

        except (MemoryError, TimeoutError, OSError) as e:
            # Classify system errors
            logger.critical(
                f"System error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                },
                exc_info=True
            )
            raise classify_system_error(e)

        except (DeepCopyValidationError, DeepCopyBusinessError, DeepCopyDatabaseError, DeepCopySystemError):
            # Re-raise our custom exceptions as-is
            raise

        except Exception as e:
            # Unknown error - log and convert to DeepCopyError
            logger.exception(
                f"Unexpected error during copy",
                extra={
                    'source_project_id': self.source.id,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            )

            from .exceptions import DeepCopyError, USER_MESSAGES
            raise DeepCopyError(
                code=9999,
                message=f"Unknown error during copy: {str(e)}",
                user_message=USER_MESSAGES[9999],
                details={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    'source_project_id': self.source.id
                }
            )

    def batch_copy(
        self,
        new_owner,
        base_name,
        count,
        new_tanggal_mulai=None,
        copy_jadwal=True,
        progress_callback=None
    ):
        """
        Copy project multiple times in one operation (FASE 3.2).

        Creates multiple copies with auto-incrementing names.
        Each copy is independent and uses a fresh DeepCopyService instance
        to avoid ID mapping conflicts.

        Args:
            new_owner: User who will own the copied projects
            base_name: Base name for projects (will append " - Copy 1", " - Copy 2", etc.)
            count: Number of copies to create (1-50)
            new_tanggal_mulai: Start date for new projects (optional)
            copy_jadwal: Whether to copy schedule data (default: True)
            progress_callback: Optional callback function(current, total, project_name)

        Returns:
            List of newly created project instances

        Raises:
            ValueError: If count is invalid
            ValidationError: If any validation fails

        Example:
            service = DeepCopyService(source_project)
            projects = service.batch_copy(
                new_owner=request.user,
                base_name="Monthly Project Template",
                count=3,
                copy_jadwal=True
            )
            # Creates:
            #   - "Monthly Project Template - Copy 1"
            #   - "Monthly Project Template - Copy 2"
            #   - "Monthly Project Template - Copy 3"
        """
        from django.core.exceptions import ValidationError as DjangoValidationError

        # Validate count
        if not isinstance(count, int) or count < 1:
            raise DjangoValidationError("Count must be a positive integer")
        if count > 50:
            raise DjangoValidationError("Maximum 50 copies allowed in one batch")

        projects = []
        errors = []

        for i in range(1, count + 1):
            # Generate unique name for this copy
            copy_name = f"{base_name} - Copy {i}"

            # Report progress
            if progress_callback:
                progress_callback(i, count, copy_name)

            try:
                # Create fresh service instance for each copy to avoid ID mapping conflicts
                service = DeepCopyService(self.source)

                # Perform the copy
                new_project = service.copy(
                    new_owner=new_owner,
                    new_name=copy_name,
                    new_tanggal_mulai=new_tanggal_mulai,
                    copy_jadwal=copy_jadwal
                )

                projects.append(new_project)

            except Exception as e:
                # Record error but continue with remaining copies
                error_msg = f"Failed to create copy {i} '{copy_name}': {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        # If all copies failed, raise an error
        if len(projects) == 0:
            raise DjangoValidationError(
                f"All {count} copies failed. Errors: {'; '.join(errors)}"
            )

        # If some copies failed, log warning
        if errors:
            logger.warning(
                f"Batch copy completed with {len(projects)}/{count} successes. "
                f"Errors: {'; '.join(errors)}"
            )

        return projects

    def _copy_project(
        self,
        new_owner,
        new_name,
        new_tanggal_mulai
    ):
        """
        Step 1: Copy the Project instance.

        Args:
            new_owner: User who will own the copied project
            new_name: Name for the new project
            new_tanggal_mulai: Start date for new project

        Returns:
            The newly created project instance
        """
        from dashboard.models import Project

        old_id = self.source.id

        # Create new project instance with required fields
        new_project = Project(
            owner=new_owner,
            nama=new_name,
            sumber_dana=self.source.sumber_dana,
            lokasi_project=self.source.lokasi_project,
            nama_client=self.source.nama_client,
            anggaran_owner=self.source.anggaran_owner,
            tanggal_mulai=new_tanggal_mulai or self.source.tanggal_mulai,
            is_active=self.source.is_active,
        )

        # Copy optional fields if they exist
        if hasattr(self.source, 'durasi_hari') and self.source.durasi_hari:
            new_project.durasi_hari = self.source.durasi_hari
        if hasattr(self.source, 'deskripsi') and self.source.deskripsi:
            new_project.deskripsi = self.source.deskripsi
        if hasattr(self.source, 'kategori') and self.source.kategori:
            new_project.kategori = self.source.kategori

        # Copy additional optional fields
        optional_fields = [
            'ket_project1', 'ket_project2', 'jabatan_client', 'instansi_client',
            'nama_kontraktor', 'instansi_kontraktor', 'nama_konsultan_perencana',
            'instansi_konsultan_perencana', 'nama_konsultan_pengawas',
            'instansi_konsultan_pengawas'
        ]
        for field in optional_fields:
            if hasattr(self.source, field):
                value = getattr(self.source, field)
                if value:
                    setattr(new_project, field, value)

        new_project.save()

        # Map IDs
        self.mappings['project'][old_id] = new_project.id

        return new_project

    def _copy_project_pricing(self, new_project):
        """
        Step 2: Copy ProjectPricing (OneToOne with Project).

        Args:
            new_project: The newly created project
        """
        try:
            old_pricing = ProjectPricing.objects.get(project=self.source)
            old_id = old_pricing.id

            new_pricing = ProjectPricing(
                project=new_project,
                ppn_percent=old_pricing.ppn_percent,
                markup_percent=old_pricing.markup_percent,
                rounding_base=old_pricing.rounding_base,
            )
            new_pricing.save()

            self.mappings['pricing'][old_id] = new_pricing.id

        except ProjectPricing.DoesNotExist:
            # If no pricing exists, skip
            pass

    def _copy_project_parameters(self, new_project):
        """
        Step 3: Copy ProjectParameter instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        parameters = ProjectParameter.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_param in parameters:
            new_param = ProjectParameter(
                project=new_project,
                name=old_param.name,
                value=old_param.value,
                label=old_param.label,
                unit=old_param.unit,
                description=old_param.description,
            )
            items_to_create.append((old_param.id, new_param))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            ProjectParameter,
            items_to_create,
            'parameter',
            batch_size=500
        )

        self.stats['parameter_copied'] = len(created)

    def _copy_klasifikasi(self, new_project):
        """
        Step 4: Copy Klasifikasi instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        klasifikasi_list = Klasifikasi.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_klas in klasifikasi_list:
            new_klas = Klasifikasi(
                project=new_project,
                name=old_klas.name,
                ordering_index=old_klas.ordering_index,  # Preserve ordering
            )
            items_to_create.append((old_klas.id, new_klas))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            Klasifikasi,
            items_to_create,
            'klasifikasi',
            batch_size=500
        )

        self.stats['klasifikasi_copied'] = len(created)

    def _copy_subklasifikasi(self, new_project):
        """
        Step 5: Copy SubKlasifikasi instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        subklas_list = SubKlasifikasi.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_subklas in subklas_list:
            old_id = old_subklas.id
            old_klasifikasi_id = old_subklas.klasifikasi_id

            # Remap FK
            new_klasifikasi_id = self.mappings['klasifikasi'].get(old_klasifikasi_id)

            if new_klasifikasi_id:
                new_subklas = SubKlasifikasi(
                    project=new_project,
                    klasifikasi_id=new_klasifikasi_id,
                    name=old_subklas.name,
                    ordering_index=old_subklas.ordering_index,  # Preserve ordering
                )
                items_to_create.append((old_id, new_subklas))
            else:
                # Track skipped item - parent Klasifikasi not found or not copied
                skipped_item = {
                    'id': old_id,
                    'name': old_subklas.name,
                    'reason': 'Parent Klasifikasi not found or not copied',
                    'missing_parent_id': old_klasifikasi_id
                }
                skipped.append(skipped_item)

                logger.warning(
                    f"Skipped SubKlasifikasi during copy - parent missing",
                    extra={
                        'source_project_id': self.source.id,
                        'subklasifikasi_id': old_id,
                        'subklasifikasi_name': old_subklas.name,
                        'missing_klasifikasi_id': old_klasifikasi_id
                    }
                )

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            SubKlasifikasi,
            items_to_create,
            'subklasifikasi',
            batch_size=500
        )

        self.stats['subklasifikasi_copied'] = len(created)
        self.skipped_items['subklasifikasi'].extend(skipped)

    def _copy_pekerjaan(self, new_project):
        """
        Step 6: Copy Pekerjaan instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        pekerjaan_list = Pekerjaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_pekerjaan in pekerjaan_list:
            old_id = old_pekerjaan.id
            old_subklas_id = old_pekerjaan.sub_klasifikasi_id

            # Remap FK
            new_subklas_id = self.mappings['subklasifikasi'].get(old_subklas_id)

            if new_subklas_id:
                new_pekerjaan = Pekerjaan(
                    project=new_project,
                    sub_klasifikasi_id=new_subklas_id,
                    snapshot_kode=old_pekerjaan.snapshot_kode,
                    snapshot_uraian=old_pekerjaan.snapshot_uraian,
                    snapshot_satuan=old_pekerjaan.snapshot_satuan,
                    source_type=old_pekerjaan.source_type,
                    ordering_index=old_pekerjaan.ordering_index,
                )
                # Copy optional fields if they exist
                if hasattr(old_pekerjaan, 'ref') and old_pekerjaan.ref:
                    new_pekerjaan.ref = old_pekerjaan.ref
                if hasattr(old_pekerjaan, 'auto_load_rincian'):
                    new_pekerjaan.auto_load_rincian = old_pekerjaan.auto_load_rincian
                if hasattr(old_pekerjaan, 'markup_override_percent') and old_pekerjaan.markup_override_percent:
                    new_pekerjaan.markup_override_percent = old_pekerjaan.markup_override_percent

                items_to_create.append((old_id, new_pekerjaan))
            else:
                # Track skipped item - parent SubKlasifikasi not found or not copied
                skipped_item = {
                    'id': old_id,
                    'kode': old_pekerjaan.snapshot_kode,
                    'uraian': old_pekerjaan.snapshot_uraian,
                    'reason': 'Parent SubKlasifikasi not found or not copied',
                    'missing_parent_id': old_subklas_id
                }
                skipped.append(skipped_item)

                logger.warning(
                    f"Skipped Pekerjaan during copy - parent missing",
                    extra={
                        'source_project_id': self.source.id,
                        'pekerjaan_id': old_id,
                        'pekerjaan_kode': old_pekerjaan.snapshot_kode,
                        'pekerjaan_uraian': old_pekerjaan.snapshot_uraian,
                        'missing_subklasifikasi_id': old_subklas_id
                    }
                )

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            Pekerjaan,
            items_to_create,
            'pekerjaan',
            batch_size=500
        )

        self.stats['pekerjaan_copied'] = len(created)
        self.skipped_items['pekerjaan'].extend(skipped)

    def _copy_volume_pekerjaan(self, new_project):
        """
        Step 7: Copy VolumePekerjaan instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        volume_list = VolumePekerjaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_volume in volume_list:
            old_id = old_volume.id
            old_pekerjaan_id = old_volume.pekerjaan_id

            # Remap FK
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)

            if new_pekerjaan_id:
                new_volume = VolumePekerjaan(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    quantity=old_volume.quantity,
                )
                items_to_create.append((old_id, new_volume))
            else:
                # Track skipped item - parent Pekerjaan not found
                skipped.append({
                    'id': old_id,
                    'reason': 'Parent Pekerjaan not found or not copied',
                    'missing_parent_id': old_pekerjaan_id
                })

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            VolumePekerjaan,
            items_to_create,
            'volume',
            batch_size=500
        )

        self.stats['volume_copied'] = len(created)
        self.skipped_items['volume'].extend(skipped)

    def _copy_harga_item(self, new_project):
        """
        Step 8: Copy HargaItem using HargaItemProject model (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        harga_list = HargaItemProject.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []
        for old_harga in harga_list:
            new_harga = HargaItemProject(
                project=new_project,
                kode_item=old_harga.kode_item,
                kategori=old_harga.kategori,
                uraian=old_harga.uraian,
                satuan=old_harga.satuan,
                harga_satuan=old_harga.harga_satuan,
            )
            items_to_create.append((old_harga.id, new_harga))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            HargaItemProject,
            items_to_create,
            'harga_item',
            batch_size=500
        )

        self.stats['harga_item_copied'] = len(created)

    def _copy_ahsp_template(self, new_project):
        """
        Step 9: Copy DetailAHSPProject instances (Optimized with bulk_create + skip tracking).

        Performance: O(1) queries instead of O(n) queries.
        Critical: This is usually the largest data volume (5-10x pekerjaan count).

        Args:
            new_project: The newly created project
        """
        ahsp_list = DetailAHSPProject.objects.filter(project=self.source)

        # Prepare instances for bulk creation and track skipped items
        items_to_create = []
        skipped = []

        for old_ahsp in ahsp_list:
            old_id = old_ahsp.id
            old_pekerjaan_id = old_ahsp.pekerjaan_id
            old_harga_item_id = old_ahsp.harga_item_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_harga_item_id = self.mappings['harga_item'].get(old_harga_item_id)

            if new_pekerjaan_id and new_harga_item_id:
                new_ahsp = DetailAHSPProject(
                    project=new_project,
                    pekerjaan_id=new_pekerjaan_id,
                    harga_item_id=new_harga_item_id,
                    kategori=old_ahsp.kategori,
                    kode=old_ahsp.kode,
                    uraian=old_ahsp.uraian,
                    satuan=old_ahsp.satuan,
                    koefisien=old_ahsp.koefisien,
                )
                # Copy ref_ahsp_id if exists (for bundle items)
                if hasattr(old_ahsp, 'ref_ahsp_id') and old_ahsp.ref_ahsp_id:
                    new_ahsp.ref_ahsp_id = old_ahsp.ref_ahsp_id

                items_to_create.append((old_id, new_ahsp))
            else:
                # Track skipped item - parent FK not found
                skipped.append({
                    'id': old_id,
                    'kode': old_ahsp.kode,
                    'uraian': old_ahsp.uraian,
                    'reason': 'Parent Pekerjaan or HargaItem not found',
                    'missing_pekerjaan_id': old_pekerjaan_id if not new_pekerjaan_id else None,
                    'missing_harga_item_id': old_harga_item_id if not new_harga_item_id else None
                })

        # Bulk create all valid items at once
        created = self._bulk_create_with_mapping(
            DetailAHSPProject,
            items_to_create,
            'ahsp_template',
            batch_size=500
        )

        self.stats['ahsp_template_copied'] = len(created)
        self.skipped_items['ahsp_template'].extend(skipped)

    def _copy_rincian_ahsp(self, new_project):
        """
        Step 10: Copy RincianAhsp instances (placeholder - model structure TBD).

        Args:
            new_project: The newly created project
        """
        # Note: RincianAhsp model structure not clear from existing code
        # This is a placeholder implementation
        # Will need to be updated based on actual model structure
        pass

    def _copy_tahapan(self, new_project):
        """
        Step 11: Copy TahapanPelaksanaan instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        tahapan_list = TahapPelaksanaan.objects.filter(project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []

        for old_tahapan in tahapan_list:
            new_tahapan = TahapPelaksanaan(
                project=new_project,
                nama=old_tahapan.nama,
                urutan=old_tahapan.urutan,
            )
            # Copy optional fields if they exist
            if hasattr(old_tahapan, 'deskripsi') and old_tahapan.deskripsi:
                new_tahapan.deskripsi = old_tahapan.deskripsi
            if hasattr(old_tahapan, 'tanggal_mulai'):
                new_tahapan.tanggal_mulai = old_tahapan.tanggal_mulai
            if hasattr(old_tahapan, 'tanggal_selesai'):
                new_tahapan.tanggal_selesai = old_tahapan.tanggal_selesai
            if hasattr(old_tahapan, 'is_auto_generated'):
                new_tahapan.is_auto_generated = old_tahapan.is_auto_generated
            if hasattr(old_tahapan, 'generation_mode') and old_tahapan.generation_mode:
                new_tahapan.generation_mode = old_tahapan.generation_mode

            items_to_create.append((old_tahapan.id, new_tahapan))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            TahapPelaksanaan,
            items_to_create,
            'tahapan',
            batch_size=500
        )

        self.stats['tahapan_copied'] = len(created)

    def _copy_jadwal_pekerjaan(self, new_project):
        """
        Step 12: Copy PekerjaanTahapan instances (Optimized with bulk_create).

        Performance: O(1) queries instead of O(n) queries.

        Args:
            new_project: The newly created project
        """
        # Filter by tahapan__project since PekerjaanTahapan doesn't have project field
        jadwal_list = PekerjaanTahapan.objects.filter(tahapan__project=self.source)

        # Prepare instances for bulk creation
        items_to_create = []

        for old_jadwal in jadwal_list:
            old_id = old_jadwal.id
            old_pekerjaan_id = old_jadwal.pekerjaan_id
            old_tahapan_id = old_jadwal.tahapan_id

            # Remap FKs
            new_pekerjaan_id = self.mappings['pekerjaan'].get(old_pekerjaan_id)
            new_tahapan_id = self.mappings['tahapan'].get(old_tahapan_id)

            if new_pekerjaan_id and new_tahapan_id:
                new_jadwal = PekerjaanTahapan(
                    pekerjaan_id=new_pekerjaan_id,
                    tahapan_id=new_tahapan_id,
                    proporsi_volume=old_jadwal.proporsi_volume,
                )
                # Copy optional fields if they exist
                if hasattr(old_jadwal, 'catatan') and old_jadwal.catatan:
                    new_jadwal.catatan = old_jadwal.catatan

                items_to_create.append((old_id, new_jadwal))

        # Bulk create all at once
        created = self._bulk_create_with_mapping(
            PekerjaanTahapan,
            items_to_create,
            'jadwal',
            batch_size=500
        )

        self.stats['jadwal_copied'] = len(created)

    # =========================================================================
    # PERFORMANCE OPTIMIZATION HELPERS (FASE 4.1)
    # =========================================================================

    def _bulk_create_with_mapping(
        self,
        model_class,
        items_data,
        mapping_key,
        batch_size=500
    ):
        """
        Bulk create items and update ID mappings efficiently.

        This method provides 10-50x performance improvement over individual save()
        calls by using Django's bulk_create() operation.

        Args:
            model_class: Django model class to create instances of
            items_data: List of (old_id, new_instance) tuples
            mapping_key: Key in self.mappings dict to store ID mappings
            batch_size: Number of objects to create per batch (default 500)

        Returns:
            List of created instances with IDs populated

        Example:
            items_to_create = [
                (old_klas.id, Klasifikasi(project=new_project, name="Klas 1")),
                (old_klas2.id, Klasifikasi(project=new_project, name="Klas 2")),
            ]
            created = self._bulk_create_with_mapping(
                Klasifikasi, items_to_create, 'klasifikasi'
            )

        Performance:
            - Before: N queries for N items
            - After: ceil(N/batch_size) queries
            - Example: 1000 items = 1000 queries → 2 queries (500+500)
        """
        if not items_data:
            return []

        # Extract old IDs and new instances
        old_ids = [old_id for old_id, _ in items_data]
        new_instances = [instance for _, instance in items_data]

        # Bulk create all instances
        # Note: bulk_create returns instances with IDs populated (Django 1.10+)
        created = model_class.objects.bulk_create(
            new_instances,
            batch_size=batch_size
        )

        # Update mappings: old_id -> new_id
        for old_id, new_instance in zip(old_ids, created):
            self.mappings[mapping_key][old_id] = new_instance.id

        logger.info(
            f"Bulk created {len(created)} {model_class.__name__} instances",
            extra={
                'model': model_class.__name__,
                'count': len(created),
                'batch_size': batch_size,
                'batches': (len(created) + batch_size - 1) // batch_size
            }
        )

        return created

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_stats(self):
        """
        Get copy statistics.

        Returns:
            Dictionary with counts of copied objects
        """
        return self.stats.copy()

    def get_warnings(self):
        """
        Get warnings collected during copy operation.

        Warnings indicate non-fatal issues that occurred during copy,
        such as skipped items due to missing parent references.

        Returns:
            List of warning dictionaries with code, message, and details
        """
        return self.warnings.copy()

    def get_skipped_items(self):
        """
        Get detailed information about items that were skipped during copy.

        Returns:
            Dictionary mapping item type to list of skipped items with details:
            {
                'subklasifikasi': [{'id': 1, 'name': '...', 'reason': '...'}],
                'pekerjaan': [{'id': 2, 'name': '...', 'reason': '...'}],
                ...
            }
        """
        return {
            k: v.copy() for k, v in self.skipped_items.items() if v
        }