"""
Test Data Setup from Exported Project JSON
==========================================

Script to import project data from existing export JSON files for load testing.
Uses the existing import_project_from_json API.

Usage:
------
# Import from backup file
python load_testing/setup_test_data.py --file backup_pre_deploy_20251118_213149.json

# Import multiple test copies
python load_testing/setup_test_data.py --file backup.json --copies 3

# List available backup files
python load_testing/setup_test_data.py --list
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse


# ============================================================================
# CONFIGURATION
# ============================================================================

# Common backup file locations
BACKUP_LOCATIONS = [
    PROJECT_ROOT,
    PROJECT_ROOT / "backups",
    PROJECT_ROOT / "load_testing" / "test_data",
]

# Extension for backup files
BACKUP_EXTENSIONS = [".json"]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def find_backup_files() -> list:
    """Find all JSON backup files in common locations"""
    backup_files = []
    
    for location in BACKUP_LOCATIONS:
        if not location.exists():
            continue
            
        for ext in BACKUP_EXTENSIONS:
            for file in location.glob(f"*{ext}"):
                # Check if it's a project backup
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        first_bytes = f.read(500)
                        if '"export_type"' in first_bytes and '"project_full_backup"' in first_bytes:
                            size_mb = file.stat().st_size / (1024 * 1024)
                            backup_files.append({
                                "path": file,
                                "name": file.name,
                                "size_mb": round(size_mb, 2),
                            })
                except Exception:
                    pass
    
    return sorted(backup_files, key=lambda x: x["name"])


def validate_backup_file(filepath: Path) -> dict:
    """Validate that file is a valid project backup"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get('export_type') != 'project_full_backup':
            return {"valid": False, "error": "Not a project backup file"}
        
        stats = data.get('stats', {})
        return {
            "valid": True,
            "project_name": data.get('project', {}).get('nama', 'Unknown'),
            "export_date": data.get('export_date', 'Unknown'),
            "export_version": data.get('export_version', '1.0'),
            "stats": stats,
        }
    
    except json.JSONDecodeError as e:
        return {"valid": False, "error": f"Invalid JSON: {e}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}


def import_project_via_api(filepath: Path, username: str) -> dict:
    """Import project using Django test client"""
    User = get_user_model()
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return {"success": False, "error": f"User '{username}' not found"}
    
    client = Client()
    client.force_login(user)
    
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    import_url = reverse('detail_project:import_project_from_json')
    
    response = client.post(
        import_url,
        data=json.dumps(data),
        content_type='application/json'
    )
    
    if response.status_code == 200:
        result = response.json()
        return {
            "success": True,
            "project_id": result.get('project_id'),
            "project_name": result.get('message', ''),
            "stats": result.get('stats', {}),
        }
    else:
        return {
            "success": False,
            "error": response.json().get('message', f"HTTP {response.status_code}"),
        }


def setup_test_projects(filepath: Path, username: str, copies: int = 1) -> list:
    """Import multiple copies of a project for load testing"""
    results = []
    
    print(f"\n{'=' * 60}")
    print("IMPORTING TEST PROJECTS")
    print(f"{'=' * 60}")
    print(f"Source: {filepath.name}")
    print(f"Copies: {copies}")
    print(f"User: {username}")
    print(f"{'=' * 60}\n")
    
    for i in range(copies):
        print(f"Importing copy {i + 1}/{copies}...", end=" ")
        
        result = import_project_via_api(filepath, username)
        
        if result["success"]:
            print(f"✓ Project ID: {result['project_id']}")
            results.append(result)
        else:
            print(f"✗ Error: {result['error']}")
            results.append(result)
    
    return results


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Setup test data for load testing from exported project JSON"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to backup JSON file"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available backup files"
    )
    parser.add_argument(
        "--user", "-u",
        type=str,
        default="admin",
        help="Username to own imported projects (default: admin)"
    )
    parser.add_argument(
        "--copies", "-c",
        type=int,
        default=1,
        help="Number of project copies to create (default: 1)"
    )
    parser.add_argument(
        "--validate", "-v",
        action="store_true",
        help="Validate backup file without importing"
    )
    
    args = parser.parse_args()
    
    # List backup files
    if args.list:
        print("\n📁 Available Backup Files:")
        print("-" * 60)
        
        backups = find_backup_files()
        if not backups:
            print("No backup files found!")
            print(f"Searched in: {[str(p) for p in BACKUP_LOCATIONS]}")
            return 1
        
        for backup in backups:
            print(f"  {backup['name']} ({backup['size_mb']} MB)")
        
        print("-" * 60)
        print(f"Total: {len(backups)} backup file(s)\n")
        return 0
    
    # Validate or import
    if not args.file:
        print("Error: --file required. Use --list to see available files.")
        return 1
    
    filepath = Path(args.file)
    if not filepath.is_absolute():
        filepath = PROJECT_ROOT / args.file
    
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        return 1
    
    # Validate
    validation = validate_backup_file(filepath)
    
    if not validation["valid"]:
        print(f"Error: Invalid backup file - {validation['error']}")
        return 1
    
    print("\n📋 Backup File Info:")
    print("-" * 60)
    print(f"  Project: {validation['project_name']}")
    print(f"  Export Date: {validation['export_date']}")
    print(f"  Version: {validation['export_version']}")
    print(f"  Stats:")
    for key, value in validation["stats"].items():
        print(f"    - {key}: {value}")
    print("-" * 60)
    
    if args.validate:
        print("\n✓ Validation successful!")
        return 0
    
    # Import
    results = setup_test_projects(filepath, args.user, args.copies)
    
    success_count = sum(1 for r in results if r.get("success"))
    
    print(f"\n{'=' * 60}")
    print(f"IMPORT COMPLETE: {success_count}/{len(results)} successful")
    print(f"{'=' * 60}")
    
    if success_count > 0:
        project_ids = [r["project_id"] for r in results if r.get("success")]
        print(f"\n📌 Project IDs for load testing: {project_ids}")
        print("\nUpdate load_testing/locustfile.py with these IDs:")
        print(f"    self.project_ids = {project_ids}")
    
    return 0 if success_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
