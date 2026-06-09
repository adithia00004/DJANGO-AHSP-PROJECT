import json
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import Klasifikasi, Pekerjaan, PekerjaanTemplate, SubKlasifikasi
from detail_project.views_api import (
    api_create_template,
    api_get_template_detail,
    api_import_template,
    api_import_template_from_file,
    api_list_templates,
)
from referensi.models import AHSPReferensi


@override_settings(SECURE_SSL_REDIRECT=False)
class TemplateLibraryApiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username="owner_template_api",
            email="owner-template-api@example.com",
            password="Secret123!",
        )
        self.other = user_model.objects.create_user(
            username="other_template_api",
            email="other-template-api@example.com",
            password="Secret123!",
        )
        for user in (self.owner, self.other):
            user.subscription_status = user.SubscriptionStatus.PRO
            user.subscription_end_date = timezone.now() + timedelta(days=30)
            user.save(update_fields=["subscription_status", "subscription_end_date"])

        self.owner_project = Project.objects.create(
            owner=self.owner,
            nama="Owner Project Template",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client Owner",
            anggaran_owner=1000,
        )
        self.other_project = Project.objects.create(
            owner=self.other,
            nama="Other Project Template",
            sumber_dana="APBN",
            lokasi_project="Bandung",
            nama_client="Client Other",
            anggaran_owner=1000,
        )
        self.factory = RequestFactory()

    def _get(self, path, user):
        request = self.factory.get(path)
        request.user = user
        return request

    def _post_json(self, path, payload, user):
        request = self.factory.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = user
        return request

    def _legacy_template_content(self):
        return {
            "klasifikasi": [
                {
                    "name": "Klasifikasi A",
                    "sub": [
                        {
                            "name": "Sub A1",
                            "pekerjaan": [
                                {
                                    "source_type": "custom",
                                    "snapshot_kode": "CST.001",
                                    "snapshot_uraian": "Pekerjaan A1",
                                    "snapshot_satuan": "m2",
                                }
                            ],
                        }
                    ],
                }
            ]
        }

    def _flat_template_content(self):
        return {
            "export_type": "project_template",
            "export_version": "3.0",
            "klasifikasi": [{"_export_id": "k1", "name": "Klasifikasi A"}],
            "sub_klasifikasi": [{"_export_id": "s1", "_klasifikasi_ref": "k1", "name": "Sub A1"}],
            "pekerjaan": [
                {
                    "_export_id": "p1",
                    "_sub_klasifikasi_ref": "s1",
                    "source_type": "custom",
                    "snapshot_kode": "CST.001",
                    "snapshot_uraian": "Pekerjaan A1",
                    "snapshot_satuan": "m2",
                }
            ],
            "detail_ahsp": [],
        }

    def test_model_stats_supports_flat_template_format(self):
        template = PekerjaanTemplate.objects.create(
            name="Template Flat Stats",
            description="Flat format stats",
            category="lainnya",
            content=self._flat_template_content(),
            created_by=self.owner,
            is_public=True,
        )
        self.assertEqual(template.total_klasifikasi, 1)
        self.assertEqual(template.total_sub, 1)
        self.assertEqual(template.total_pekerjaan, 1)

    def test_list_templates_includes_public_and_own_private(self):
        public_template = PekerjaanTemplate.objects.create(
            name="Template Public Shared",
            description="Public",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=True,
        )
        owner_private_template = PekerjaanTemplate.objects.create(
            name="Template Owner Private",
            description="Owner private",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=False,
        )
        other_private_template = PekerjaanTemplate.objects.create(
            name="Template Other Private",
            description="Other private",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.other,
            is_public=False,
        )

        request = self._get("/api/templates/", self.owner)
        response = api_list_templates(request)
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        ids = {item["id"] for item in body.get("templates", [])}
        self.assertIn(public_template.id, ids)
        self.assertIn(owner_private_template.id, ids)
        self.assertNotIn(other_private_template.id, ids)

    def test_private_template_detail_blocked_for_non_creator(self):
        private_template = PekerjaanTemplate.objects.create(
            name="Template Private Detail",
            description="Private detail",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=False,
        )

        request = self._get(f"/api/templates/{private_template.id}/", self.other)
        response = api_get_template_detail(request, private_template.id)
        self.assertEqual(response.status_code, 404)

    def test_private_template_detail_allowed_for_creator(self):
        private_template = PekerjaanTemplate.objects.create(
            name="Template Private Creator",
            description="Private creator detail",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=False,
        )

        request = self._get(f"/api/templates/{private_template.id}/", self.owner)
        response = api_get_template_detail(request, private_template.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(json.loads(response.content.decode("utf-8")).get("ok"))

    def test_import_private_template_blocked_for_non_creator(self):
        private_template = PekerjaanTemplate.objects.create(
            name="Template Private Import",
            description="Private import",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=False,
        )

        request = self._post_json(
            f"/api/project/{self.other_project.id}/templates/{private_template.id}/import/",
            {},
            self.other,
        )
        response = api_import_template(request, self.other_project.id, private_template.id)
        self.assertEqual(response.status_code, 404)

    def test_import_public_template_allowed_for_other_user(self):
        public_template = PekerjaanTemplate.objects.create(
            name="Template Public Import",
            description="Public import",
            category="lainnya",
            content=self._legacy_template_content(),
            created_by=self.owner,
            is_public=True,
        )

        request = self._post_json(
            f"/api/project/{self.other_project.id}/templates/{public_template.id}/import/",
            {},
            self.other,
        )
        response = api_import_template(request, self.other_project.id, public_template.id)
        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

        self.assertEqual(Klasifikasi.objects.filter(project=self.other_project).count(), 1)
        self.assertEqual(SubKlasifikasi.objects.filter(project=self.other_project).count(), 1)
        self.assertEqual(Pekerjaan.objects.filter(project=self.other_project).count(), 1)

        public_template.refresh_from_db()
        self.assertEqual(public_template.usage_count, 1)

    def test_import_template_from_file_does_not_leak_internal_error_detail(self):
        request = self._post_json(
            f"/api/project/{self.owner_project.id}/templates/import-file/",
            {"content": self._legacy_template_content()},
            self.owner,
        )
        with patch("detail_project.views_api._import_template_data", side_effect=RuntimeError("secret-token-123")):
            with self.assertLogs("detail_project.views_api", level="ERROR"):
                response = api_import_template_from_file(request, self.owner_project.id)

        self.assertEqual(response.status_code, 500)
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertEqual(body.get("message"), "Terjadi kesalahan saat memproses import template")
        self.assertNotIn("secret-token-123", response.content.decode("utf-8"))

    def test_create_template_from_project(self):
        classification = Klasifikasi.objects.create(
            project=self.owner_project,
            name="Klasifikasi Simpan",
            ordering_index=1,
        )
        sub = SubKlasifikasi.objects.create(
            project=self.owner_project,
            klasifikasi=classification,
            name="Sub Simpan",
            ordering_index=1,
        )
        Pekerjaan.objects.create(
            project=self.owner_project,
            sub_klasifikasi=sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-0001",
            snapshot_uraian="Pekerjaan Simpan",
            snapshot_satuan="m2",
            ordering_index=1,
        )
        request = self._post_json(
            f"/api/project/{self.owner_project.id}/templates/create/",
            {
                "name": "Template Create Regression",
                "description": "Created by API",
                "category": "lainnya",
            },
            self.owner,
        )

        response = api_create_template(
            request,
            self.owner_project.id,
        )

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        template = PekerjaanTemplate.objects.get(
            pk=body["template_id"],
        )
        self.assertEqual(template.created_by, self.owner)
        self.assertEqual(template.total_pekerjaan, 1)

    def test_template_frontend_resolves_csrf_before_post(self):
        with open(
            "detail_project/static/detail_project/js/list_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        self.assertIn("function getCsrfToken()", script)
        self.assertIn("const csrfToken = getCsrfToken();", script)
        self.assertNotIn("catch (err) {\n        templateList", script)

    def test_template_frontend_reload_after_import_is_clean(self):
        with open(
            "detail_project/static/detail_project/js/list_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        self.assertIn("await reloadAfterSave();", script)
        self.assertNotIn("await loadTree();  // Refresh data\n        setDirty(true);", script)

    def test_template_frontend_save_uses_dataset_ref_fallback(self):
        with open(
            "detail_project/static/detail_project/js/list_pekerjaan.js",
            encoding="utf-8",
        ) as handle:
            script = handle.read()

        self.assertIn("refRaw = tr.dataset.refId || tr.dataset.originalRefId || '';", script)

    def test_import_template_preserves_ref_modified_from_ref_ahsp_id(self):
        ref = AHSPReferensi.objects.create(
            kode_ahsp="8.8.8.8",
            nama_ahsp="Pekerjaan Referensi",
            satuan="m2",
            sumber="AHSP TEST",
        )
        template = PekerjaanTemplate.objects.create(
            name="Template Ref Modified",
            description="Ref modified import",
            category="lainnya",
            content={
                "klasifikasi": [
                    {
                        "name": "Klasifikasi Ref",
                        "sub": [
                            {
                                "name": "Sub Ref",
                                "pekerjaan": [
                                    {
                                        "source_type": "ref_modified",
                                        "ref_ahsp_id": ref.id,
                                        "snapshot_kode": "mod.1-8.8.8.8",
                                        "snapshot_uraian": "Pekerjaan Referensi Edit",
                                        "snapshot_satuan": "m2",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            created_by=self.owner,
            is_public=True,
        )
        request = self._post_json(
            f"/api/project/{self.owner_project.id}/templates/{template.id}/import/",
            {},
            self.owner,
        )

        response = api_import_template(
            request,
            self.owner_project.id,
            template.id,
        )

        self.assertEqual(response.status_code, 200, response.content.decode("utf-8"))
        pekerjaan = Pekerjaan.objects.get(project=self.owner_project)
        self.assertEqual(pekerjaan.source_type, Pekerjaan.SOURCE_REF_MOD)
        self.assertEqual(pekerjaan.ref_id, ref.id)
