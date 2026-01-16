"""Test script for per-period export debugging"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_ahsp.settings')
django.setup()

import traceback
from detail_project.exports.export_manager import ExportManager
from dashboard.models import Project

try:
    p = Project.objects.get(id=109)
    print(f"Project: {p}")
    
    em = ExportManager(p)
    
    time_scope = {
        'mode': 'week_range',
        'start': '2026-W02',
        'end': '2026-W03'
    }
    
    print(f"Calling export with time_scope: {time_scope}")
    result = em.export_rekap_kebutuhan('pdf', time_scope=time_scope)
    print(f"SUCCESS: {type(result)}")
    
except Exception as e:
    print(f"ERROR: {e}")
    traceback.print_exc()
