from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase

from referensi.models_staging import AHSPImportStaging
from referensi.services.import_schema import dump_workbook
from referensi.views.import_views import _create_staging_row, _stage_rincian_from_interchange


class ImportStagingValidationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="staging-validation-admin",
            email="staging-validation-admin@example.com",
            password="Secret123!",
        )
        self.client.force_login(self.user)

    def test_rejects_shifted_long_kode_item_with_clear_message(self):
        long_shifted_text = "Uraian panjang yang seharusnya tidak masuk kode item " * 3
        with self.assertRaisesMessage(ValueError, "Kolom kode_item terlalu panjang"):
            _create_staging_row(
                user=self.user,
                file_name="shifted-long-code.xlsx",
                sumber="AHSP 2026",
                parent_ahsp_code="1.2.3.4",
                segment_type="A",
                kode_item=long_shifted_text,
                uraian_item="Pekerja",
                satuan_item="OH",
                koefisien=1,
                is_valid=True,
            )

        AHSPImportStaging.objects.filter(user=self.user, file_name="shifted-long-code.xlsx").delete()

    def test_interchange_import_rejects_shifted_numbered_rows(self):
        workbook = dump_workbook(
            [
                {
                    "kode_ahsp": "3.5.2.2.1",
                    "nama_ahsp": "Pemasangan plafon",
                    "segmen": "B",
                    "no": "",
                    "kode_item": "Plafon Serat Semen/GRC Tebal 4 mm Termasuk Alat Pasang",
                    "uraian": "1",
                    "satuan": "m2",
                    "koefisien": "1.21",
                }
            ],
            {"sumber": "AHSP 2026"},
        )

        with self.assertRaisesMessage(ValueError, "WARNING: Kolom Bergeser"):
            _stage_rincian_from_interchange(
                self.user,
                "shifted-interchange.xlsx",
                BytesIO(workbook),
                "",
            )
