from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0041_projectchangestatus_pending_flags"),
    ]

    operations = [
        migrations.CreateModel(
            name="TemplateAhspKoefFormulaState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("row_key", models.CharField(max_length=100)),
                ("raw", models.TextField(blank=True, default="")),
                ("is_fx", models.BooleanField(default=True)),
                (
                    "pekerjaan",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="template_ahsp_koef_formula_states",
                        to="detail_project.pekerjaan",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="template_ahsp_koef_formula_states",
                        to="dashboard.project",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="templateahspkoefformulastate",
            constraint=models.UniqueConstraint(
                fields=("project", "pekerjaan", "row_key"),
                name="uniq_ta_koef_formula_per_row",
            ),
        ),
        migrations.AddIndex(
            model_name="templateahspkoefformulastate",
            index=models.Index(fields=["project", "pekerjaan"], name="ta_koef_proj_pkj_idx"),
        ),
        migrations.AddIndex(
            model_name="templateahspkoefformulastate",
            index=models.Index(fields=["project", "pekerjaan", "row_key"], name="ta_koef_proj_row_idx"),
        ),
    ]
