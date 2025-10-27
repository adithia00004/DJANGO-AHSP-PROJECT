# Generated manually for weekly canonical storage implementation
#
# This migration adds PekerjaanProgressWeekly model which serves as the
# single source of truth for progress data in weekly units.
#
# Key changes:
# - New PekerjaanProgressWeekly model (canonical storage)
# - PekerjaanTahapan becomes a derived/view layer
#
# Migration strategy:
# 1. Create new table
# 2. Data migration will populate from existing PekerjaanTahapan (separate step)

from django.db import migrations, models
import django.db.models.deletion
from django.core.validators import MinValueValidator, MaxValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0012_tahapan_auto_generation_fields'),
        ('dashboard', '0001_initial'),  # For Project FK
    ]

    operations = [
        migrations.CreateModel(
            name='PekerjaanProgressWeekly',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),

                # Week identification
                ('week_number', models.IntegerField(help_text='Week number starting from 1 (relative to project start date)')),
                ('week_start_date', models.DateField(help_text='Start date of this week')),
                ('week_end_date', models.DateField(help_text='End date of this week')),

                # Progress data
                ('proportion', models.DecimalField(
                    decimal_places=2,
                    max_digits=5,
                    validators=[MinValueValidator(0.01), MaxValueValidator(100.00)],
                    help_text='Proportion of work (%) completed in this week. Range: 0.01 - 100.00'
                )),

                # Metadata
                ('notes', models.TextField(blank=True, help_text="Optional notes for this week's progress")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),

                # Foreign Keys
                ('pekerjaan', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='weekly_progress',
                    to='detail_project.pekerjaan'
                )),
                ('project', models.ForeignKey(
                    help_text='Denormalized for easier querying',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='pekerjaan_weekly_progress',
                    to='dashboard.project'
                )),
            ],
            options={
                'verbose_name': 'Weekly Progress Pekerjaan',
                'verbose_name_plural': 'Weekly Progress Pekerjaan',
                'ordering': ['pekerjaan', 'week_number'],
                'unique_together': {('pekerjaan', 'week_number')},
                'indexes': [
                    models.Index(fields=['pekerjaan', 'week_number'], name='detail_proj_pekerjaan_week_idx'),
                    models.Index(fields=['project', 'week_number'], name='detail_proj_project_week_idx'),
                    models.Index(fields=['week_start_date', 'week_end_date'], name='detail_proj_week_dates_idx'),
                ],
            },
        ),
    ]
