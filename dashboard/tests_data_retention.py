from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import RequestFactory, TestCase

from dashboard.admin import ProjectAdmin
from dashboard.models import Project


class ProjectRetentionPolicyTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.owner = self.user_model.objects.create_user(
            username="owner_retention",
            email="owner_retention@example.com",
            password="StrongPass123!",
        )
        self.project = Project.objects.create(owner=self.owner, nama="Project Retention")

    def test_owner_delete_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.owner.delete()

    def test_admin_hard_delete_is_disabled(self):
        admin = ProjectAdmin(Project, AdminSite())
        request = RequestFactory().get("/admin/dashboard/project/")
        self.assertFalse(admin.has_delete_permission(request, obj=self.project))
