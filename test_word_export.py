"""Test script to reproduce Word export error"""
import os
import sys
import traceback

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from detail_project.models import Project
from detail_project.exports.export_manager import ExportManager

def test_word_export():
    try:
        print("[TEST] Getting project 109...")
        p = Project.objects.get(id=109)
        print(f"[TEST] Project: {p}")
        
        print("[TEST] Creating ExportManager...")
        m = ExportManager(p)
        
        print("[TEST] Calling export_rekap_rab('word')...")
        result = m.export_rekap_rab('word')
        print('[TEST] Success:', type(result))
        return True
    except Exception as e:
        print(f"[TEST] ERROR: {e}")
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_word_export()
