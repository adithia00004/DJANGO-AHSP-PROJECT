import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0009_remove_tanggal_mulai_default"),
        ("detail_project", "0018_detailahspexpanded_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DetailAHSPAudit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(
                        default=django.utils.timezone.now, editable=False
                    ),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "action",
                    models.CharField(
                        choices=[
                            ("CREATE", "Create"),
                            ("UPDATE", "Update"),
                            ("DELETE", "Delete"),
                            ("CASCADE", "Cascade Re-expansion"),
                        ],
                        max_length=10,
                    ),
                ),
                ("old_data", models.JSONField(blank=True, null=True)),
                ("new_data", models.JSONField(blank=True, null=True)),
                (
                    "triggered_by",
                    models.CharField(
                        choices=[
                            ("user", "User"),
                            ("cascade", "Cascade"),
                            ("system", "System"),
                        ],
                        default="user",
                        max_length=20,
                    ),
                ),
                ("change_summary", models.TextField(blank=True)),
                (
                    "pekerjaan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="audit_entries",
                        to="detail_project.pekerjaan",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detail_audit_entries",
                        to="dashboard.project",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="detailahspaudit",
            index=models.Index(
                fields=["project", "-created_at"],
                name="audit_project_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="detailahspaudit",
            index=models.Index(
                fields=["pekerjaan", "-created_at"],
                name="audit_pekerjaan_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="detailahspaudit",
            index=models.Index(fields=["action"], name="audit_action_idx"),
        ),
    ]
