#!/usr/bin/env python
"""
Script to regenerate tahapan for project 83 with fixed weekly logic.

This will:
1. Delete old auto-generated tahapan
2. Generate new weekly tahapan with correct boundaries (Senin-Minggu)
3. Sync progress from canonical storage

Usage:
    python regenerate_project_83.py
"""

import os
import sys
import pathlib

# --- Make sure Python can import your project packages (add project root to sys.path)
BASE_DIR = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))  # project root containing manage.py and 'config/'

# --- Point to the correct Django settings module (your project uses 'config')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from django.db import transaction
from dashboard.models import Project
from detail_project.models import TahapPelaksanaan, PekerjaanTahapan
from detail_project.views_api_tahapan import _generate_weekly_tahapan
from detail_project.progress_utils import sync_weekly_to_tahapan

PROJECT_ID = 83


@transaction.atomic
def regenerate_tahapan():
    """Regenerate tahapan for project 83"""

    # Get project
    try:
        project = Project.objects.get(id=PROJECT_ID)
    except Project.DoesNotExist:
        print(f"❌ Project {PROJECT_ID} not found!")
        return

    # Safety: handle None tanggal_mulai / tanggal_selesai gracefully
    def _fmt(d):
        return f"{d} ({d.strftime('%A')})" if d else "-"

    print(f"Project: {getattr(project, 'nama', project.id)}")
    print(f"  Start: {_fmt(getattr(project, 'tanggal_mulai', None))}")
    print(f"  End: {_fmt(getattr(project, 'tanggal_selesai', None))}\n")

    # STEP 1: Delete old auto-generated tahapan
    print("STEP 1: Deleting old auto-generated tahapan...")
    old_qs = TahapPelaksanaan.objects.filter(project=project, is_auto_generated=True)
    count_old = old_qs.count()
    print(f"  Found {count_old} auto-generated tahapan")

    if count_old:
        print("\n  OLD TAHAPAN (akan dihapus):")
        for tahap in old_qs.order_by('urutan')[:5]:
            print(f"    - {tahap.nama}")
        if count_old > 5:
            print(f"    ... and {count_old - 5} more")

        deleted_count, _ = old_qs.delete()
        print(f"  ✓ Deleted {deleted_count} tahapan\n")
    else:
        print("  ✓ No auto-generated tahapan to delete\n")

    # STEP 2: Generate new weekly tahapan with CORRECT defaults
    print("STEP 2: Generating new weekly tahapan...")
    print("  Using: week_start_day=0 (Senin), week_end_day=6 (Minggu)")

    new_tahapan = _generate_weekly_tahapan(
        project,
        week_start_day=0,  # Monday
        week_end_day=6     # Sunday
    )

    print(f"  Generated {len(new_tahapan)} new tahapan")

    print("\n  NEW TAHAPAN:")
    for tahap in new_tahapan[:10]:
        days = (tahap.tanggal_selesai - tahap.tanggal_mulai).days + 1
        print(f"    - {tahap.nama} ({days} hari)")
    if len(new_tahapan) > 10:
        print(f"    ... and {len(new_tahapan) - 10} more")

    created = TahapPelaksanaan.objects.bulk_create(new_tahapan)
    print(f"  ✓ Created {len(created)} tahapan\n")

    # STEP 3: Sync assignments from canonical storage
    print("STEP 3: Syncing assignments from canonical storage...")
    synced_count = sync_weekly_to_tahapan(
        project.id,
        mode='weekly',
        week_end_day=6  # Sunday
    )
    print(f"  ✓ Synced {synced_count} assignments\n")

    print("=" * 60)
    print("✅ SUCCESS! Tahapan regenerated with correct weekly boundaries.")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Refresh browser halaman Jadwal Pekerjaan")
    print("2. Verifikasi interval weekly sudah benar")
    print("3. Jika masih salah, cek console browser untuk error")


if __name__ == '__main__':
    regenerate_tahapan()
