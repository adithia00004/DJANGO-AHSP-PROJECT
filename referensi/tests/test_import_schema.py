from io import BytesIO

from django.test import SimpleTestCase

from referensi.services.import_schema import (
    SCHEMA_VERSION,
    dump_workbook,
    is_interchange_workbook,
    load_workbook_rows,
)


class ImportSchemaServiceTests(SimpleTestCase):
    def test_dump_and_load_interchange_workbook(self):
        workbook = dump_workbook(
            [
                {
                    "kode_ahsp": "2.2.1.1.5.a",
                    "nama_ahsp": "Pekerjaan A",
                    "segmen": "TK",
                    "kode_item": "L.01",
                    "uraian": "Pekerja",
                    "satuan": "OH",
                    "koefisien": "1,5",
                }
            ],
            {"sumber": "AHSP 2026", "export_type": "valid"},
        )

        self.assertTrue(is_interchange_workbook(BytesIO(workbook)))
        rows, meta = load_workbook_rows(BytesIO(workbook))

        self.assertEqual(meta["schema_version"], SCHEMA_VERSION)
        self.assertEqual(meta["sumber"], "AHSP 2026")
        self.assertEqual(rows[0]["kode_ahsp"], "2.2.1.1.5.a")
        self.assertEqual(rows[0]["nama_ahsp"], "Pekerjaan A")
        self.assertEqual(rows[0]["segmen"], "A")
        self.assertEqual(rows[0]["koefisien"], "1.5")
