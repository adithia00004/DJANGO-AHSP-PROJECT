from django.test import TestCase

from referensi.models import KodeItemReferensi
from referensi.services.item_code_registry import resolve_item_code
from referensi.services.item_code_registry import assign_item_codes
from types import SimpleNamespace


class RuntimeItemCodeRegistryTests(TestCase):
    def test_source_code_is_not_part_of_runtime_identity(self):
        first = resolve_item_code("TK", "Tukang Pipa", "OH")
        second = resolve_item_code("TK", "Tukang Pipa", "OH")

        self.assertEqual(first, second)
        self.assertRegex(first, r"^TK-\d{4}$")

    def test_different_semantics_receive_different_codes(self):
        pipe = resolve_item_code("TK", "Tukang Pipa", "OH")
        wood = resolve_item_code("TK", "Tukang Kayu", "OH")

        self.assertNotEqual(pipe, wood)
        self.assertEqual(
            KodeItemReferensi.objects.filter(kategori="TK").count(),
            2,
        )

    def test_import_assignment_ignores_source_file_code(self):
        KodeItemReferensi.objects.create(
            kategori="TK",
            uraian_item="Tukang Pipa",
            satuan_item="OH",
            kode_item="TK-0045",
        )
        detail = SimpleNamespace(
            kategori="TK",
            kategori_source="TK",
            uraian_item="Tukang Pipa",
            satuan_item="OH",
            kode_item="L.02",
            kode_item_source="manual",
        )
        parsed = SimpleNamespace(
            jobs=[SimpleNamespace(rincian=[detail])]
        )

        stats = assign_item_codes(parsed)

        self.assertEqual(detail.kode_item, "TK-0045")
        self.assertEqual(detail.kode_item_source, "existing")
        self.assertEqual(stats.reused, 1)
