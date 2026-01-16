import os
import sys
import django

sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from referensi.models import AHSPReferensi

total = AHSPReferensi.objects.count()
print(f'Total AHSP records: {total}')

if total > 0:
    first_5 = AHSPReferensi.objects.all()[:5]
    print('\nFirst 5 records:')
    for ahsp in first_5:
        print(f'  - {ahsp.kode_ahsp}: {ahsp.nama_ahsp[:60]}')
