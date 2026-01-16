import pytest

from referensi.models import AHSPReferensi, RincianReferensi


@pytest.mark.django_db
def test_ahsp_history_tracks_create_and_update():
    ahsp = AHSPReferensi.objects.create(
        kode_ahsp="1.1.1",
        nama_ahsp="Pekerjaan Tanah",
        sumber="SNI 2025",
    )

    history_types = list(ahsp.history.values_list("history_type", flat=True))
    assert history_types == ["+"], "Initial create should record a history row"

    ahsp.nama_ahsp = "Pekerjaan Tanah (revisi)"
    ahsp.save()

    history_types = list(ahsp.history.values_list("history_type", flat=True))
    assert history_types[0] == "~"
    assert history_types[1] == "+"


@pytest.mark.django_db
def test_rincian_history_tracks_delete():
    ahsp = AHSPReferensi.objects.create(
        kode_ahsp="1.1.2",
        nama_ahsp="Pekerjaan Pondasi",
    )
    rincian = RincianReferensi.objects.create(
        ahsp=ahsp,
        kategori=RincianReferensi.Kategori.TK,
        kode_item="TK-001",
        uraian_item="Pekerja Terampil",
        satuan_item="OH",
        koefisien="1.0",
    )

    history_before = list(
        RincianReferensi.history.filter(id=rincian.id).values_list("history_type", flat=True)
    )
    assert history_before == ["+"]

    rincian_id = rincian.id
    rincian.delete()
    history_types = list(
        RincianReferensi.history.filter(id=rincian_id).values_list("history_type", flat=True)
    )
    assert history_types[0] == "-"
    assert history_types[1] == "+"
