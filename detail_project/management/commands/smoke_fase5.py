# === Smoke 5 (minimal, set PID dulu) ===
PID = 82  # <-- GANTI ke project_id kamu

from decimal import Decimal, ROUND_HALF_UP
from django.urls import reverse
from django.test import Client
from django.db.models import Max
from dashboard.models import Project
from detail_project.models import (
    Pekerjaan, VolumePekerjaan, DetailAHSPProject,
    Klasifikasi, SubKlasifikasi
)
from referensi.models import AHSPReferensi

# -- Resolve project & owner
project = Project.objects.get(id=PID, is_active=True)
owner = project.owner

# -- Pastikan ada SubKlasifikasi (karena Pekerjaan.sub_klasifikasi NOT NULL)
sub = (SubKlasifikasi.objects
       .select_related('klasifikasi')
       .filter(klasifikasi__project=project)
       .first())
if not sub:
    klas = Klasifikasi.objects.create(project=project, name='QA', ordering_index=0)
    sub  = SubKlasifikasi.objects.create(klasifikasi=klas, name='S1', ordering_index=0)

# -- Pastikan ada pekerjaan CUSTOM
pj_custom = (Pekerjaan.objects
             .filter(project=project, source_type='custom')
             .first())
if not pj_custom:
    next_idx = (Pekerjaan.objects.filter(project=project)
                .aggregate(Max('ordering_index'))['ordering_index__max'] or 0) + 1
    pj_custom = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type='custom',
        snapshot_kode='CUST-SMOKE-001',
        snapshot_uraian='Custom Smoke Bundle',
        snapshot_satuan='OH',
        ordering_index=next_idx,
    )
    print(f"[create] CUSTOM: id={pj_custom.id} kode={pj_custom.snapshot_kode}")

# -- Client
c = Client(); c.force_login(owner); c.defaults['HTTP_HOST'] = 'localhost'

# -- Seed 1 TK + 1 LAIN(bundle) bila perlu
ref = AHSPReferensi.objects.first()
assert ref, "Tabel AHSPReferensi kosong—import referensi dulu."

need_smoke  = not DetailAHSPProject.objects.filter(project=project, pekerjaan=pj_custom, kategori='TK',   kode='TK.SMOKE').exists()
need_bundle = not DetailAHSPProject.objects.filter(project=project, pekerjaan=pj_custom, kategori='LAIN', kode='BUNDLE-1').exists()

if need_smoke or need_bundle:
    save_url = reverse('detail_project:api_save_detail_ahsp_for_pekerjaan',
                       kwargs={'project_id': project.id, 'pekerjaan_id': pj_custom.id})
    payload = {
        "rows":[
            {"kategori":"TK","kode":"TK.SMOKE","uraian":"TK Smoke","satuan":"OH","koefisien":"0.125"},
            {"kategori":"LAIN","kode":"BUNDLE-1","uraian":"Bundle test","satuan":None,"koefisien":"2","ref_ahsp_id":ref.id},
        ]
    }
    print("[save]", c.post(save_url, data=payload, content_type='application/json').json())

# -- Set volume
VolumePekerjaan.objects.update_or_create(
    project=project, pekerjaan=pj_custom, defaults={"quantity": Decimal("5.000")}
)
print("[volume] OK")

# -- API rekap
rk_api = reverse('detail_project:api_get_rekap_kebutuhan', kwargs={'project_id': project.id})
js = c.get(rk_api).json()
rows = js.get('rows', [])
print("[rekap] rows:", len(rows))

# -- Ambil qty TK.SMOKE dari API
from decimal import Decimal
def api_qty(kode):
    r = next((r for r in rows if r.get('kode') == kode), None)
    return Decimal(r['quantity']) if r else None

# -- Hitung expected total TK.SMOKE = sum(koef * volume) seluruh pekerjaan
def expected_total_for(kode):
    total = Decimal('0')
    for d in DetailAHSPProject.objects.filter(project=project, kode=kode).values('pekerjaan_id','koefisien'):
        vol = (VolumePekerjaan.objects
               .filter(project=project, pekerjaan_id=d['pekerjaan_id'])
               .values_list('quantity', flat=True).first()) or Decimal('0')
        total += Decimal(str(d['koefisien'])) * vol
    return total.quantize(Decimal('0.000001'))

got = api_qty('TK.SMOKE')
exp = expected_total_for('TK.SMOKE')
print("TK.SMOKE API=", got, "EXPECTED=", exp)
assert got == exp, f"Mismatch TK.SMOKE total: API={got} vs EXP={exp}"
print("✅ Smoke Fase 5 OK")
