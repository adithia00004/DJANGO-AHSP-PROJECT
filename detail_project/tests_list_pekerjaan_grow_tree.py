"""Regresi: menambah pekerjaan ke pohon yang sudah terisi.

Gejala yang dilaporkan owner 2026-09-22 pada project 219: menyimpan pohon
gagal 500 dengan `UniqueViolation ... (project_id, ordering_index)=(219, 36)`,
padahal data di database bersih (35 baris, indeks 1..35 semuanya unik).

Sebabnya rentang parkir tumpang tindih dengan rentang final. Sebelum menyusun
ulang, baris lama dipindah ke slot sementara `max + idx` -- 35 baris jadi
diparkir di 36..70. Begitu pohon TUMBUH satu baris, posisi final ke-36
menabrak baris parkir di 36. Karena itu menyusun ulang tanpa menambah tetap
berhasil, sementara menambah SELALU gagal.
"""

import json

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse

from dashboard.models import Project
from detail_project.models import Pekerjaan
from detail_project.views_api import api_upsert_list_pekerjaan


class GrowTreeUpsertTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="grow-tree-owner", password="StrongPass123!"
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Tumbuh",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas",
            anggaran_owner=1000000,
        )
        self.factory = RequestFactory()
        self.url = reverse(
            "detail_project:api_upsert_list_pekerjaan",
            kwargs={"project_id": self.project.id},
        )

    def _tree(self, jobs):
        """jobs = daftar (ordering_index, id|None)."""
        return {
            "klasifikasi": [
                {
                    "name": "Klas A",
                    "ordering_index": 1,
                    "sub": [
                        {
                            "name": "Sub A1",
                            "ordering_index": 1,
                            "pekerjaan": [
                                {
                                    **({"id": pid} if pid is not None else {}),
                                    "source_type": "custom",
                                    "ordering_index": oi,
                                    "snapshot_uraian": f"Job {oi}",
                                    "snapshot_satuan": "m2",
                                }
                                for oi, pid in jobs
                            ],
                        }
                    ],
                }
            ]
        }

    def _save(self, jobs):
        request = self.factory.post(
            self.url,
            data=json.dumps(self._tree(jobs)),
            content_type="application/json",
        )
        request.user = self.owner
        return api_upsert_list_pekerjaan(request, self.project.id)

    def _seed(self, count):
        """Buat `count` pekerjaan, kembalikan id terurut ordering_index."""
        response = self._save([(i, None) for i in range(1, count + 1)])
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        return list(
            Pekerjaan.objects.filter(project=self.project)
            .order_by("ordering_index")
            .values_list("id", flat=True)
        )

    def test_adding_a_job_to_an_existing_tree_succeeds(self):
        """Inti bug: baris lama dibawa BY ID (cabang "Update biasa"), pohon tumbuh.

        Tanpa `id`, baris masuk jalur reuse-pool dan bug ini tidak muncul --
        itulah sebabnya versi pertama tes ini hijau meski perbaikan dicabut.
        """
        ids = self._seed(5)

        # Semua baris lama tetap di posisi asalnya (jadi ditunda sebagai
        # "unchanged" dan slot parkirnya BELUM dibebaskan), lalu satu baris baru
        # ditambahkan di ujung -- posisi final 6 menabrak slot parkir 6.
        jobs = [(i + 1, pid) for i, pid in enumerate(ids)] + [(6, None)]
        response = self._save(jobs)

        self.assertEqual(
            response.status_code,
            200,
            f"menambah pekerjaan gagal: {response.content.decode('utf-8')[:300]}",
        )
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 6)

    def test_ordering_index_is_contiguous_after_growth(self):
        """Tidak ada sisa nilai parkir yang tertinggal di database."""
        ids = self._seed(4)
        jobs = [(i + 1, pid) for i, pid in enumerate(ids)] + [(5, None), (6, None)]
        self.assertEqual(self._save(jobs).status_code, 200)

        orders = sorted(
            Pekerjaan.objects.filter(project=self.project).values_list(
                "ordering_index", flat=True
            )
        )
        self.assertEqual(orders, [1, 2, 3, 4, 5, 6])

    def test_new_row_in_the_middle_like_project_219(self):
        """Bentuk nyata project 219: baris baru disisipkan di TENGAH."""
        ids = self._seed(6)
        jobs = (
            [(1, ids[0]), (2, ids[1])]
            + [(3, None)]
            + [(i + 4, pid) for i, pid in enumerate(ids[2:])]
        )
        response = self._save(jobs)

        self.assertEqual(
            response.status_code, 200, response.content.decode("utf-8")[:300]
        )
        self.assertEqual(Pekerjaan.objects.filter(project=self.project).count(), 7)
