from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from referensi.models import AHSPReferensi, KodeItemReferensi, RincianReferensi


class RepairAhspItemCodesTests(TestCase):
    def setUp(self):
        self.ahsp = AHSPReferensi.objects.create(
            kode_ahsp="TEST.1",
            nama_ahsp="Test",
            sumber="AHSP TEST",
        )
        self.existing = RincianReferensi.objects.create(
            ahsp=self.ahsp,
            kategori="ALT",
            kode_item="-",
            uraian_item="Gergaji",
            satuan_item="hari",
            koefisien="0.1",
        )
        self.generated = RincianReferensi.objects.create(
            ahsp=self.ahsp,
            kategori="BHN",
            kode_item="-",
            uraian_item="Material Baru",
            satuan_item="kg",
            koefisien="1",
        )
        self.misaligned = RincianReferensi.objects.create(
            ahsp=self.ahsp,
            kategori="TK",
            kode_item="L.02",
            uraian_item="Tukang Kayu",
            satuan_item="OH",
            koefisien="1",
        )
        KodeItemReferensi.objects.create(
            kategori="ALT",
            uraian_item="Gergaji",
            satuan_item="hari",
            kode_item="PR-0042",
        )
        KodeItemReferensi.objects.create(
            kategori="TK",
            uraian_item="Tukang Kayu",
            satuan_item="OH",
            kode_item="TK-0003",
        )

    def test_command_is_dry_run_then_reuses_and_generates_codes(self):
        call_command(
            "repair_ahsp_item_codes",
            source="AHSP TEST",
            stdout=StringIO(),
        )
        self.existing.refresh_from_db()
        self.assertEqual(self.existing.kode_item, "-")

        call_command(
            "repair_ahsp_item_codes",
            source="AHSP TEST",
            apply=True,
            stdout=StringIO(),
        )
        self.existing.refresh_from_db()
        self.generated.refresh_from_db()
        self.misaligned.refresh_from_db()

        self.assertEqual(self.existing.kode_item, "PR-0042")
        self.assertRegex(self.generated.kode_item, r"^B-\d{4}$")
        self.assertEqual(self.misaligned.kode_item, "TK-0003")
        self.assertTrue(
            KodeItemReferensi.objects.filter(
                kategori="BHN",
                uraian_item="Material Baru",
                satuan_item="kg",
                kode_item=self.generated.kode_item,
            ).exists()
        )
