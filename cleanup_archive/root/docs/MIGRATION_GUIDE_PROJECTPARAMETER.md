# 🔧 Migration Guide: ProjectParameter Model

**Migration File**: `detail_project/migrations/0015_projectparameter.py`
**Model**: `detail_project.models.ProjectParameter`
**Created**: 2025-11-06

---

## 📋 Pre-Migration Checklist

- [x] Model created in `detail_project/models.py`
- [x] Migration file generated (`0015_projectparameter.py`)
- [x] Code committed and pushed to branch
- [ ] Database backup created (recommended)
- [ ] Migration tested on local environment

---

## 🚀 Migration Instructions

### Step 1: Pull Latest Code

```bash
git pull origin claude/check-main-branch-011CUpcdbJTospboGng9QZ3T
```

### Step 2: Verify Migration File Exists

```bash
ls detail_project/migrations/0015_projectparameter.py
```

Expected output: File should exist

### Step 3: Check Migration Status

```bash
python manage.py showmigrations detail_project
```

Expected output:
```
detail_project
  [X] 0001_initial
  [X] 0002_volumeformulastate
  ...
  [X] 0014_rename_detail_proj_pekerjaan_week_idx_detail_proj_pekerja_27e8a7_idx_and_more
  [ ] 0015_projectparameter  ← Should be unchecked (not applied yet)
```

### Step 4: Run Migration

```bash
python manage.py migrate detail_project
```

Expected output:
```
Operations to perform:
  Apply all migrations: detail_project
Running migrations:
  Applying detail_project.0015_projectparameter... OK
```

### Step 5: Verify Migration Success

```bash
python manage.py showmigrations detail_project
```

Expected output:
```
detail_project
  ...
  [X] 0015_projectparameter  ← Should now be checked (applied)
```

### Step 6: Verify Table Created

Open Django shell:

```bash
python manage.py shell
```

Run verification:

```python
from detail_project.models import ProjectParameter
from django.db import connection

# Check if table exists
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'detail_project_projectparameter';
    """)
    result = cursor.fetchone()
    print(f"Table exists: {result is not None}")

# Check table structure
print("\nTable columns:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'detail_project_projectparameter'
        ORDER BY ordinal_position;
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} (nullable: {row[2]})")

# Check indexes
print("\nTable indexes:")
with connection.cursor() as cursor:
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'detail_project_projectparameter';
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}")
```

Expected output:
```
Table exists: True

Table columns:
  id: bigint (nullable: NO)
  created_at: timestamp with time zone (nullable: NO)
  updated_at: timestamp with time zone (nullable: NO)
  name: character varying (nullable: NO)
  value: numeric (nullable: NO)
  label: character varying (nullable: YES)
  unit: character varying (nullable: YES)
  description: text (nullable: YES)
  project_id: bigint (nullable: NO)

Table indexes:
  detail_project_projectparameter_pkey
  detail_project_projectparameter_project_id_name_...
  detail_proj_project_6c8b4e_idx
```

---

## ✅ Post-Migration Testing

### Test 1: Create ProjectParameter

```python
from detail_project.models import ProjectParameter
from dashboard.models import Project
from decimal import Decimal

# Get or create a test project
project = Project.objects.filter(owner__username='your_username').first()

# Create parameter
param = ProjectParameter.objects.create(
    project=project,
    name='panjang',
    value=Decimal('10.500'),
    label='Panjang (m)',
    unit='meter',
    description='Parameter panjang untuk perhitungan volume'
)

print(f"Created: {param}")
print(f"ID: {param.id}")
```

Expected output:
```
Created: PRJ-2025-XXX - panjang = 10.500 meter
ID: 1
```

### Test 2: Read ProjectParameter

```python
# Get all parameters for project
params = ProjectParameter.objects.filter(project=project)
print(f"Total parameters: {params.count()}")

for p in params:
    print(f"  {p.name} = {p.value} {p.unit}")
```

Expected output:
```
Total parameters: 1
  panjang = 10.500 meter
```

### Test 3: Update ProjectParameter

```python
param.value = Decimal('12.000')
param.save()

param.refresh_from_db()
print(f"Updated value: {param.value}")
```

Expected output:
```
Updated value: 12.000
```

### Test 4: Unique Constraint Test

```python
# Try to create duplicate (should fail)
try:
    duplicate = ProjectParameter.objects.create(
        project=project,
        name='panjang',  # Same name!
        value=Decimal('5.000')
    )
except Exception as e:
    print(f"Expected error: {type(e).__name__}")
    print(f"Message: {str(e)}")
```

Expected output:
```
Expected error: IntegrityError
Message: duplicate key value violates unique constraint "detail_project_projectparameter_project_id_name_..."
```

### Test 5: Name Validation Test

```python
from django.core.exceptions import ValidationError

# Test space in name (should fail)
try:
    param = ProjectParameter(
        project=project,
        name='koef beton',  # Has space!
        value=Decimal('1.2')
    )
    param.save()
except ValidationError as e:
    print(f"Validation error: {e.message_dict}")
```

Expected output:
```
Validation error: {'name': ['Parameter name cannot contain spaces. Use underscore instead (e.g., "koef_beton")']}
```

### Test 6: Auto-Lowercase Test

```python
param = ProjectParameter.objects.create(
    project=project,
    name='LEBAR',  # Uppercase
    value=Decimal('5.250'),
    label='Lebar (m)',
    unit='meter'
)

print(f"Saved name: {param.name}")  # Should be lowercase
```

Expected output:
```
Saved name: lebar
```

### Test 7: Cleanup

```python
# Delete test parameters
ProjectParameter.objects.filter(project=project).delete()
print("Cleanup complete")
```

---

## 🔧 Troubleshooting

### Issue: Migration already applied

**Symptom**:
```
No migrations to apply.
```

**Solution**: Migration already ran successfully. Skip to verification step.

---

### Issue: Migration conflicts

**Symptom**:
```
CommandError: Conflicting migrations detected
```

**Solution**:
```bash
# Check migration status
python manage.py showmigrations detail_project

# If conflicted, try:
python manage.py migrate detail_project --fake-initial
```

---

### Issue: Database connection error

**Symptom**:
```
django.db.utils.OperationalError: connection to server failed
```

**Solution**:
1. Ensure PostgreSQL service is running
2. Check database credentials in settings
3. Test connection: `psql -U username -d database_name`

---

### Issue: Column already exists

**Symptom**:
```
ProgrammingError: column "name" of relation "detail_project_projectparameter" already exists
```

**Solution**: Table already exists. Either:
1. Skip migration: `python manage.py migrate detail_project --fake 0015`
2. Or rollback: `python manage.py migrate detail_project 0014` then re-run

---

## 📊 Expected Database Schema

### Table: `detail_project_projectparameter`

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| id | bigint | NO | AUTO |
| created_at | timestamp | NO | now() |
| updated_at | timestamp | NO | now() |
| name | varchar(100) | NO | - |
| value | numeric(18,3) | NO | - |
| label | varchar(200) | YES | '' |
| unit | varchar(50) | YES | '' |
| description | text | YES | '' |
| project_id | bigint | NO | FK |

### Constraints

- **PRIMARY KEY**: `id`
- **FOREIGN KEY**: `project_id` → `dashboard_project(id)` ON DELETE CASCADE
- **UNIQUE**: `(project_id, name)` - Satu project tidak boleh punya parameter dengan nama sama

### Indexes

- `detail_project_projectparameter_pkey` (PRIMARY KEY on id)
- `detail_project_projectparameter_project_id_name_...` (UNIQUE on project_id, name)
- `detail_proj_project_6c8b4e_idx` (INDEX on project_id, name)

---

## ✅ Success Criteria

Migration successful if:

- [x] Migration applied without errors
- [x] Table `detail_project_projectparameter` exists
- [x] All columns present with correct types
- [x] Unique constraint working (cannot create duplicate project+name)
- [x] Foreign key constraint working (project_id references dashboard_project)
- [x] Validation working (no spaces in name, auto-lowercase)
- [x] CRUD operations working (Create, Read, Update, Delete)

---

## 📝 Next Steps After Migration

1. ✅ Verify migration success (all tests passing)
2. Create API endpoints for parameter management
3. Update Volume Pekerjaan page to use database parameters (instead of localStorage)
4. Implement parameter import/export from localStorage
5. Test deep copy with parameters
6. Deploy to production

---

## 🆘 Need Help?

If you encounter issues:

1. Check error messages carefully
2. Review troubleshooting section above
3. Check Django logs: `tail -f logs/django.log`
4. Ask for assistance with full error traceback

---

**Migration prepared by**: Claude AI
**Date**: 2025-11-06
**Branch**: `claude/check-main-branch-011CUpcdbJTospboGng9QZ3T`
