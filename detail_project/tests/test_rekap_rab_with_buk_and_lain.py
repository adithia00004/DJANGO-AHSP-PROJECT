import pytest
from decimal import Decimal
from django.urls import reverse
from django.utils import timezone  # NEW
from dashboard.models import Project
from detail_project.models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, DetailAHSPProject, HargaItemProject, ProjectPricing
)

@pytest.mark.django_db
def test_rekap_includes_lain_and_buk(client, django_user_model):
    user = django_user_model.objects.create_user(username="u2", password="p2")
    client.login(username="u2", password="p2")
    p = Project.objects.create(
        owner=user,
        nama="P2",
        is_active=True,
        tahun_project=timezone.now().year,  # NEW
        anggaran_owner=Decimal('0'),
    )

    # struktur minimal
    k = Klasifikasi.objects.create(project=p, name="K", ordering_index=1)
    s = SubKlasifikasi.objects.create(project=p, klasifikasi=k, name="S", ordering_index=1)
    pkj = Pekerjaan.objects.create(project=p, sub_klasifikasi=s, source_type=Pekerjaan.SOURCE_CUSTOM,
                                   snapshot_kode="CUST-1", snapshot_uraian="U1", ordering_index=1)

    # master harga
    tk = HargaItemProject.objects.create(project=p, kode_item="TK.1", kategori="TK", uraian="TK1", satuan="OH", harga_satuan=Decimal("100000"))
    bh = HargaItemProject.objects.create(project=p, kode_item="B.1",  kategori="BHN", uraian="B1",  satuan="kg", harga_satuan=Decimal("20000"))
    al = HargaItemProject.objects.create(project=p, kode_item="A.1",  kategori="ALT", uraian="A1",  satuan="jam", harga_satuan=Decimal("50000"))
    ln = HargaItemProject.objects.create(project=p, kode_item="L.1",  kategori="LAIN", uraian="L1",  satuan="ls", harga_satuan=Decimal("30000"))

    # detail (koefisien)
    DetailAHSPProject.objects.create(project=p, pekerjaan=pkj, harga_item=tk, kategori="TK",  kode="TK.1",  uraian="TK1",  satuan="OH",  koefisien=Decimal("1.0"))
    DetailAHSPProject.objects.create(project=p, pekerjaan=pkj, harga_item=bh, kategori="BHN", kode="B.1",   uraian="B1",   satuan="kg",  koefisien=Decimal("2.0"))
    DetailAHSPProject.objects.create(project=p, pekerjaan=pkj, harga_item=al, kategori="ALT", kode="A.1",   uraian="A1",   satuan="jam", koefisien=Decimal("3.0"))
    DetailAHSPProject.objects.create(project=p, pekerjaan=pkj, harga_item=ln, kategori="LAIN",kode="L.1",   uraian="L1",   satuan="ls",  koefisien=Decimal("4.0"))

    # volume 1.0 supaya total == G
    from detail_project.models import VolumePekerjaan
    VolumePekerjaan.objects.create(project=p, pekerjaan=pkj, quantity=Decimal("1.000"))

    # BUK = 10%
    ProjectPricing.objects.create(project=p, markup_percent=Decimal("10.00"))

    # panggil API rekap
    url = reverse("detail_project:api_get_rekap_rab", args=[p.id])
    r = client.get(url)
    j = r.json()
    assert r.status_code == 200 and j["ok"] is True
    row = [x for x in j["rows"] if x["pekerjaan_id"] == pkj.id][0]

    A = row["A"]   # 1.0 * 100000 = 100000
    B = row["B"]   # 2.0 * 20000  = 40000
    C = row["C"]   # 3.0 * 50000  = 150000
    L = row["LAIN"]# 4.0 * 30000  = 120000
    assert A == 100000.0 and B == 40000.0 and C == 150000.0 and L == 120000.0

    E_base = row["E_base"]         # 410000
    F = row["F"]                   # 410000 * 0.10 = 41000
    G = row["G"]                   # 451000
    assert E_base == 410000.0
    assert round(F,2) == 41000.00
    assert round(G,2) == 451000.00

    assert round(row["total"],2) == 451000.00  # volume = 1.0
