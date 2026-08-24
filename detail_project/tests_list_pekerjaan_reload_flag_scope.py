"""SYN-01: flag "detail perlu dimuat ulang" harus sempit, bukan seluruh proyek.

Sebelum perbaikan, `api_upsert_list_pekerjaan` menambahkan SETIAP pekerjaan yang
hadir di payload ke `source_change_state["reload_jobs"]` -- pernyataan itu berada
di luar cabang `replace`, jadi cabang "Update biasa" (reorder / rename / pindah
sub) ikut menandai barisnya.

Halaman List Pekerjaan selalu mengirim POHON PENUH (`collectTree`), sehingga satu
save biasa menandai seluruh pekerjaan proyek. Dampaknya lintas halaman:

  * Template AHSP menampilkan banner "N pekerjaan memiliki perubahan sumber ..."
    untuk seluruh proyek dan menawarkan reload massal, padahal tidak ada satu pun
    komposisi AHSP yang berubah;
  * Harga Items mengunci seluruh input harga selama flag itu belum bersih
    (`harga_items.js` -> `updateSyncLockState`);
  * Rincian AHSP membuang cache detail untuk semua pekerjaan.

Test ini mengunci kontraknya: flag hanya untuk baris yang benar-benar berganti
sumber (SSOT `_is_reset_change`, dipakai bersama preview destructive-impact N2)
atau baris yang baru dibuat.

Dokumen: `Review/R5_Detail_Project/36_Cross_Page_Sync_Over_Notification_Audit_Plan_20260824.md`
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    ProjectChangeStatus,
    SubKlasifikasi,
)
from detail_project.services import get_pending_source_change_flags
from detail_project.views_api import api_upsert_list_pekerjaan
from referensi.models import AHSPReferensi, RincianReferensi


class ListPekerjaanReloadFlagScopeTests(TestCase):
    def setUp(self):
        # Limiter write (20/60s) memakai LocMemCache proses-wide. File ini
        # mengirim banyak upsert; bersihkan agar tidak ada 429 palsu saat
        # dijalankan lewat `manage.py test` (conftest pytest tidak aktif di sana).
        cache.clear()

        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_reload_flag_scope",
            email="owner-reload-flag-scope@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Project Reload Flag Scope",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client A",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

        self.ref_a = self._make_ref("A.1", "Master A.1")
        self.ref_b = self._make_ref("A.2", "Master A.2")

        self._seed_tree()

        # Seeding membuat 3 pekerjaan BARU, dan baris baru memang sah ditandai.
        # `change_flags` pada response melaporkan set pending KUMULATIF milik
        # proyek (hasil merge di `register_source_change_flags`), bukan delta
        # satu save. Bersihkan tracker supaya tiap test mengukur delta-nya
        # sendiri, bukan sisa seeding.
        ProjectChangeStatus.objects.filter(project=self.project).update(
            pending_reload_job_ids=[], pending_volume_reset_job_ids=[],
        )

    # ---------- helpers ----------

    def _make_ref(self, kode, nama):
        ref = AHSPReferensi.objects.create(
            kode_ahsp=kode, nama_ahsp=nama, sumber="AHSP 2025", satuan="m2",
        )
        RincianReferensi.objects.create(
            ahsp=ref, kategori="TK", kode_item="L.01", uraian_item="Pekerja",
            satuan_item="OH", koefisien=Decimal("5"),
        )
        return ref

    def _post_upsert(self, payload):
        request = self.factory.post(
            self.url, data=json.dumps(payload), content_type="application/json",
        )
        request.user = self.owner
        return api_upsert_list_pekerjaan(request, self.project.id)

    def _save(self, payload):
        """Kirim payload, pastikan 200, kembalikan body JSON."""
        resp = self._post_upsert(payload)
        self.assertEqual(resp.status_code, 200, resp.content.decode("utf-8"))
        return json.loads(resp.content.decode("utf-8"))

    @staticmethod
    def _reload_flags(body):
        """`change_flags` hanya dikirim bila ada flag; absen == tidak ada flag."""
        return sorted((body.get("change_flags") or {}).get("reload_job_ids") or [])

    def _seed_tree(self):
        """Klas 1 / Sub 1: P1 custom + P2 ref-A ; Sub 2: P3 custom."""
        self._save({
            "klasifikasi": [{
                "name": "Klas 1",
                "ordering_index": 1,
                "sub": [
                    {
                        "name": "Sub 1",
                        "ordering_index": 1,
                        "pekerjaan": [
                            {
                                "temp_id": "t1",
                                "source_type": "custom",
                                "ordering_index": 1,
                                "snapshot_uraian": "Galian tanah",
                                "snapshot_satuan": "m3",
                            },
                            {
                                "temp_id": "t2",
                                "source_type": "ref",
                                "ordering_index": 2,
                                "ref_id": self.ref_a.id,
                            },
                        ],
                    },
                    {
                        "name": "Sub 2",
                        "ordering_index": 2,
                        "pekerjaan": [
                            {
                                "temp_id": "t3",
                                "source_type": "custom",
                                "ordering_index": 3,
                                "snapshot_uraian": "Urugan pasir",
                                "snapshot_satuan": "m3",
                            },
                        ],
                    },
                ],
            }]
        })
        self.p1, self.p2, self.p3 = list(
            Pekerjaan.objects.filter(project=self.project).order_by("ordering_index")
        )

    def _current_tree(self):
        """Tiru `collectTree()`: kirim POHON PENUH beserta id, seperti frontend."""
        payload = {"klasifikasi": []}
        for k in Klasifikasi.objects.filter(project=self.project).order_by("ordering_index"):
            k_node = {"id": k.id, "name": k.name, "ordering_index": k.ordering_index, "sub": []}
            subs = SubKlasifikasi.objects.filter(
                project=self.project, klasifikasi=k
            ).order_by("ordering_index")
            for s in subs:
                s_node = {
                    "id": s.id, "name": s.name,
                    "ordering_index": s.ordering_index, "pekerjaan": [],
                }
                jobs = Pekerjaan.objects.filter(
                    project=self.project, sub_klasifikasi=s
                ).order_by("ordering_index")
                for p in jobs:
                    row = {
                        "id": p.id,
                        "source_type": p.source_type,
                        "ordering_index": p.ordering_index,
                        "snapshot_uraian": p.snapshot_uraian,
                        "snapshot_satuan": p.snapshot_satuan,
                    }
                    if p.ref_id:
                        row["ref_id"] = p.ref_id
                    s_node["pekerjaan"].append(row)
                k_node["sub"].append(s_node)
            payload["klasifikasi"].append(k_node)
        return payload

    @staticmethod
    def _find_job(tree, pekerjaan_id):
        for k in tree["klasifikasi"]:
            for s in k["sub"]:
                for p in s["pekerjaan"]:
                    if p.get("id") == pekerjaan_id:
                        return p
        raise AssertionError(f"pekerjaan {pekerjaan_id} tidak ada di payload")

    # ---------- F1-F4: save non-destruktif tidak boleh menandai apa pun ----------

    def test_f1_identical_resave_flags_nothing(self):
        body = self._save(self._current_tree())
        self.assertEqual(self._reload_flags(body), [])

    def test_f2_rename_klasifikasi_flags_nothing(self):
        tree = self._current_tree()
        tree["klasifikasi"][0]["name"] = "Pekerjaan Persiapan"
        body = self._save(tree)
        self.assertEqual(self._reload_flags(body), [])
        self.assertEqual(
            Klasifikasi.objects.get(project=self.project).name, "Pekerjaan Persiapan"
        )

    def test_f3_reorder_pekerjaan_flags_nothing(self):
        tree = self._current_tree()
        sub1 = tree["klasifikasi"][0]["sub"][0]
        sub1["pekerjaan"][0]["ordering_index"] = 2
        sub1["pekerjaan"][1]["ordering_index"] = 1
        sub1["pekerjaan"].reverse()

        body = self._save(tree)
        self.assertEqual(self._reload_flags(body), [])

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p2.ordering_index, 1)
        self.assertEqual(self.p1.ordering_index, 2)

    def test_f4_move_pekerjaan_between_sub_flags_nothing(self):
        tree = self._current_tree()
        sub1, sub2 = tree["klasifikasi"][0]["sub"]
        moved = sub2["pekerjaan"].pop()
        sub1["pekerjaan"].append(moved)

        body = self._save(tree)
        self.assertEqual(self._reload_flags(body), [])

        self.p3.refresh_from_db()
        self.assertEqual(self.p3.sub_klasifikasi_id, sub1["id"])

    # ---------- F5-F7: perubahan sumber & baris baru TETAP ditandai ----------

    def test_f5_change_ref_id_flags_only_that_job(self):
        tree = self._current_tree()
        self._find_job(tree, self.p2.id)["ref_id"] = self.ref_b.id

        body = self._save(tree)
        self.assertEqual(self._reload_flags(body), [self.p2.id])

        self.p2.refresh_from_db()
        self.assertEqual(self.p2.ref_id, self.ref_b.id)

    def test_f6_change_source_type_ref_to_custom_flags_only_that_job(self):
        tree = self._current_tree()
        row = self._find_job(tree, self.p2.id)
        row["source_type"] = "custom"
        row["snapshot_uraian"] = "Pekerjaan kustom baru"
        row["snapshot_satuan"] = "m2"
        row.pop("ref_id", None)

        body = self._save(tree)
        self.assertEqual(self._reload_flags(body), [self.p2.id])

        self.p2.refresh_from_db()
        self.assertEqual(self.p2.source_type, Pekerjaan.SOURCE_CUSTOM)

    def test_f7_new_pekerjaan_flags_only_the_new_row(self):
        tree = self._current_tree()
        tree["klasifikasi"][0]["sub"][0]["pekerjaan"].append({
            "temp_id": "new-1",
            "source_type": "custom",
            "ordering_index": 4,
            "snapshot_uraian": "Pekerjaan tambahan",
            "snapshot_satuan": "m2",
        })

        body = self._save(tree)
        new_id = body["id_map"]["pekerjaan"]["new-1"]
        self.assertEqual(self._reload_flags(body), [new_id])
        self.assertNotIn(self.p1.id, self._reload_flags(body))

    # ---------- F8: flag tidak menumpuk di tracker persisten ----------

    def test_f8_repeated_non_destructive_saves_leave_tracker_empty(self):
        for _ in range(3):
            body = self._save(self._current_tree())
            self.assertEqual(self._reload_flags(body), [])

        flags = get_pending_source_change_flags(self.project)
        self.assertEqual(flags["reload_job_ids"], [])

    def test_f8b_source_change_persists_then_stays_scoped(self):
        """Regresi arah sebaliknya: flag yang SAH harus tetap tersimpan di tracker,
        dan save biasa berikutnya tidak boleh menambah pekerjaan lain ke dalamnya."""
        tree = self._current_tree()
        self._find_job(tree, self.p2.id)["ref_id"] = self.ref_b.id
        self._save(tree)

        self.assertEqual(
            get_pending_source_change_flags(self.project)["reload_job_ids"],
            [self.p2.id],
        )

        body = self._save(self._current_tree())
        self.assertEqual(self._reload_flags(body), [])
        self.assertEqual(
            get_pending_source_change_flags(self.project)["reload_job_ids"],
            [self.p2.id],
        )
