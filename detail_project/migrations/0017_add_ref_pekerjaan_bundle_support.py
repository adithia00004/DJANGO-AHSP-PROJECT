# Generated manually for bundle support to Pekerjaan
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0016_rename_detail_proj_project_6c8b4e_idx_detail_proj_project_541dd2_idx'),
    ]

    operations = [
        # Add ref_pekerjaan field to DetailAHSPProject
        migrations.AddField(
            model_name='detailahspproject',
            name='ref_pekerjaan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='bundle_references',
                to='detail_project.pekerjaan',
                help_text='Reference to another Pekerjaan in same project (bundle support)'
            ),
        ),

        # Remove old constraint
        migrations.RemoveConstraint(
            model_name='detailahspproject',
            name='ref_ahsp_only_for_lain',
        ),

        # Add new constraints
        migrations.AddConstraint(
            model_name='detailahspproject',
            constraint=models.CheckConstraint(
                check=Q(
                    Q(ref_ahsp__isnull=True, ref_pekerjaan__isnull=True) |
                    Q(kategori='LAIN')
                ),
                name='bundle_ref_only_for_lain'
            ),
        ),

        # Constraint: Only ONE type of reference (ahsp OR pekerjaan, not both)
        migrations.AddConstraint(
            model_name='detailahspproject',
            constraint=models.CheckConstraint(
                check=~Q(ref_ahsp__isnull=False, ref_pekerjaan__isnull=False),
                name='bundle_ref_exclusive'
            ),
        ),
    ]
