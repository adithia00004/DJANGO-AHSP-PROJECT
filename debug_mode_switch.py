"""
Debug script untuk investigate mode switching bug.

Run this in Django shell to diagnose the issue:
python manage.py shell < debug_mode_switch.py
"""

from detail_project.models import PekerjaanProgressWeekly, PekerjaanTahapan, TahapPelaksanaan, Pekerjaan
from dashboard.models import Project
from decimal import Decimal

# Test Project ID (ganti dengan project yang Anda test)
PROJECT_ID = 83  # Pembangunan Gedung Serbaguna (Copy)

print("\n" + "="*70)
print("DEBUGGING MODE SWITCHING BUG")
print("="*70 + "\n")

project = Project.objects.get(id=PROJECT_ID)
print(f"Project: {project.nama}")
print(f"Start: {project.tanggal_mulai}, End: {project.tanggal_selesai}\n")

# Get a sample pekerjaan with weekly data
sample_weekly = PekerjaanProgressWeekly.objects.filter(
    project=project
).first()

if not sample_weekly:
    print("❌ No weekly progress data found!")
    exit()

pekerjaan = sample_weekly.pekerjaan
print(f"Sample Pekerjaan: {pekerjaan.snapshot_uraian}\n")

# Show CANONICAL data (should NEVER change!)
print("📊 CANONICAL DATA (PekerjaanProgressWeekly):")
print("-" * 70)
weekly_data = PekerjaanProgressWeekly.objects.filter(
    pekerjaan=pekerjaan
).order_by('week_number')

canonical_total = Decimal('0.00')
for w in weekly_data:
    print(f"  Week {w.week_number}: {w.proportion}% "
          f"({w.week_start_date} to {w.week_end_date}, "
          f"{(w.week_end_date - w.week_start_date).days + 1} days)")
    canonical_total += w.proportion

print(f"\n  CANONICAL TOTAL: {canonical_total}%")
print("  ☝️ This should NEVER change after mode switches!\n")

# Show VIEW LAYER data (can be regenerated)
print("📋 VIEW LAYER DATA (PekerjaanTahapan):")
print("-" * 70)
tahapan_data = PekerjaanTahapan.objects.filter(
    pekerjaan=pekerjaan
).select_related('tahapan').order_by('tahapan__urutan')

view_total = Decimal('0.00')
for t in tahapan_data:
    tahap = t.tahapan
    days = (tahap.tanggal_selesai - tahap.tanggal_mulai).days + 1 if tahap.tanggal_mulai and tahap.tanggal_selesai else 0
    print(f"  {tahap.nama}: {t.proporsi_volume}% "
          f"({tahap.tanggal_mulai} to {tahap.tanggal_selesai}, "
          f"{days} days, mode={tahap.generation_mode})")
    view_total += t.proporsi_volume

print(f"\n  VIEW TOTAL: {view_total}%")
print("  ☝️ This can be regenerated from canonical\n")

# Check for discrepancy
discrepancy = abs(float(canonical_total - view_total))
if discrepancy > 0.01:
    print(f"⚠️  WARNING: Discrepancy detected: {discrepancy:.2f}%")
    print("     Canonical and view layer don't match!\n")
else:
    print("✅ Canonical and view layer match!\n")

# Show current tahapan structure
print("🏗️  CURRENT TAHAPAN STRUCTURE:")
print("-" * 70)
all_tahapan = TahapPelaksanaan.objects.filter(
    project=project
).order_by('urutan')[:10]  # First 10 only

for t in all_tahapan:
    days = (t.tanggal_selesai - t.tanggal_mulai).days + 1 if t.tanggal_mulai and t.tanggal_selesai else 0
    print(f"  [{t.urutan}] {t.nama} ({t.generation_mode}, {days} days)")

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("1. Note the CANONICAL TOTAL above")
print("2. Switch modes in browser (Weekly → Monthly → Weekly)")
print("3. Run this script again")
print("4. Compare CANONICAL TOTAL - should be IDENTICAL!")
print("\nIf CANONICAL changes, we have a serious bug!")
print("If only VIEW changes, it's expected (view is regenerated)")
print("="*70 + "\n")
