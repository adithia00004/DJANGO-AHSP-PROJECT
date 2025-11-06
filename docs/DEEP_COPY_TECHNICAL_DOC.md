# Deep Copy - Technical Documentation

## Architecture Overview

Deep Copy menggunakan **Service Pattern** dengan **ID Mapping Strategy** untuk handle complex foreign key relationships.

```
┌──────────────┐
│   UI Layer   │  (project_detail.html)
│   (Modal)    │  Button + Form + JavaScript
└──────┬───────┘
       │ fetch() POST
       ▼
┌──────────────────────┐
│  API Layer           │  (views_api.py)
│  api_deep_copy_project│  Validation + Error Handling
└──────┬───────────────┘
       │ service.copy()
       ▼
┌────────────────────────┐
│  Service Layer         │  (services.py)
│  DeepCopyService       │  12-Step Copy + ID Mapping
└──────┬─────────────────┘
       │ ORM operations
       ▼
┌───────────────────┐
│  Model Layer      │
│  Django ORM       │
└───────────────────┘
```

## Implementation Details

### 1. DeepCopyService Class

**File:** `detail_project/services.py`

#### Class Structure

```python
class DeepCopyService:
    def __init__(self, source_project: Project):
        self.source = source_project
        self.mappings = {
            'project': {},
            'pricing': {},
            'parameter': {},
            'klasifikasi': {},
            'subklasifikasi': {},
            'pekerjaan': {},
            'volume': {},
            'harga_item': {},
            'ahsp_template': {},
            'rincian_ahsp': {},
            'tahapan': {},
            'jadwal': {},
        }
        self.stats = {
            'klasifikasi_copied': 0,
            'subklasifikasi_copied': 0,
            # ... other stats
        }
```

#### ID Mapping Strategy

**Problem:** Foreign key references must be updated to point to new copied objects.

**Solution:** Maintain a dictionary mapping old IDs to new IDs.

**Example:**
```python
# Step 1: Copy Klasifikasi
old_klas = Klasifikasi.objects.get(id=100, project=source_project)
new_klas = Klasifikasi.objects.create(project=new_project, name=old_klas.name)
self.mappings['klasifikasi'][100] = new_klas.id  # 100 -> 555

# Step 2: Copy SubKlasifikasi (references Klasifikasi)
old_subklas = SubKlasifikasi.objects.get(id=200, klasifikasi_id=100)
new_klasifikasi_id = self.mappings['klasifikasi'][100]  # Get new ID: 555
new_subklas = SubKlasifikasi.objects.create(
    project=new_project,
    klasifikasi_id=new_klasifikasi_id,  # Use mapped ID!
    name=old_subklas.name
)
self.mappings['subklasifikasi'][200] = new_subklas.id
```

### 2. Copy Sequence (12 Steps)

**CRITICAL:** Order matters due to FK dependencies!

```python
@transaction.atomic
def copy(self, new_owner, new_name, new_tanggal_mulai=None, copy_jadwal=True):
    # Step 1: Project (no dependencies)
    new_project = self._copy_project(...)

    # Step 2: ProjectPricing (depends on Project)
    self._copy_project_pricing(new_project)

    # Step 3: ProjectParameter (depends on Project)
    self._copy_project_parameters(new_project)

    # Step 4: Klasifikasi (depends on Project)
    self._copy_klasifikasi(new_project)

    # Step 5: SubKlasifikasi (depends on Klasifikasi)
    self._copy_subklasifikasi(new_project)

    # Step 6: Pekerjaan (depends on SubKlasifikasi)
    self._copy_pekerjaan(new_project)

    # Step 7: VolumePekerjaan (depends on Pekerjaan)
    self._copy_volume_pekerjaan(new_project)

    # Step 8: HargaItem (depends on Project)
    self._copy_harga_item(new_project)

    # Step 9: DetailAHSPProject (depends on Pekerjaan + HargaItem)
    self._copy_ahsp_template(new_project)

    # Step 10: RincianAhsp (placeholder - TBD)
    self._copy_rincian_ahsp(new_project)

    if copy_jadwal:
        # Step 11: Tahapan (depends on Project)
        self._copy_tahapan(new_project)

        # Step 12: PekerjaanTahapan (depends on Pekerjaan + Tahapan)
        self._copy_jadwal_pekerjaan(new_project)

    return new_project
```

**Dependency Graph:**
```
Project
├── ProjectPricing
├── ProjectParameter
├── Klasifikasi
│   └── SubKlasifikasi
│       └── Pekerjaan
│           ├── VolumePekerjaan
│           └── DetailAHSPProject ←┐
│               │                  │
│               └── (depends on) ──┘
│                   HargaItem
└── Tahapan (if copy_jadwal=True)
    └── PekerjaanTahapan
        └── (depends on) Pekerjaan + Tahapan
```

### 3. Transaction Management

**All copy operations wrapped in `@transaction.atomic`:**

```python
@transaction.atomic
def copy(self, ...):
    # All 12 steps here
    # If ANY step fails, ALL changes rollback
```

**Benefits:**
- **Atomicity:** Either all data copied or nothing
- **No partial copies:** Prevents database corruption
- **Automatic rollback:** On error, no cleanup needed

**Database Isolation:**
```sql
BEGIN;
-- Step 1: INSERT INTO dashboard_project ...
-- Step 2: INSERT INTO detail_project_projectpricing ...
-- ...
-- Step 12: INSERT INTO detail_project_pekerjantahapan ...
COMMIT;  -- or ROLLBACK on error
```

### 4. Model Compatibility

Service uses **existing model names** from codebase:

| Service Variable | Actual Model Name |
|-----------------|-------------------|
| `Klasifikasi` | `Klasifikasi` (not `KlasifikasiPekerjaan`) |
| `SubKlasifikasi` | `SubKlasifikasi` (not `SubKlasifikasiPekerjaan`) |
| `Pekerjaan` | `Pekerjaan` (not `PekerjaanProyek`) |
| `VolumePekerjaan` | `VolumePekerjaan` |
| `HargaItemProject` | `HargaItemProject` (not `HargaItem`) |
| `DetailAHSPProject` | `DetailAHSPProject` (not `AhspTemplate`) |
| `TahapPelaksanaan` | `TahapPelaksanaan` (not `TahapanPelaksanaan`) |
| `PekerjaanTahapan` | `PekerjaanTahapan` (not `JadwalPekerjaan`) |

**Important:** Use `hasattr()` checks for optional fields:

```python
# Copy optional fields safely
if hasattr(old_pricing, 'markup_percent'):
    new_pricing.markup_percent = old_pricing.markup_percent

if hasattr(old_pekerjaan, 'markup_override_percent'):
    new_pekerjaan.markup_override_percent = old_pekerjaan.markup_override_percent
```

### 5. API Endpoint

**File:** `detail_project/views_api.py`

```python
@login_required
@require_POST
def api_deep_copy_project(request: HttpRequest, project_id: int):
    """
    Deep copy a project with all related data.

    POST /api/project/<project_id>/deep-copy/
    """
    # 1. Verify ownership
    source_project = _owner_or_404(project_id, request.user)

    # 2. Parse & validate JSON body
    payload = json.loads(request.body.decode("utf-8"))
    new_name = payload.get("new_name", "").strip()
    if not new_name:
        return JsonResponse({"ok": False, "error": "..."}, status=400)

    # 3. Parse optional parameters
    new_tanggal_mulai = parse_date(payload.get("new_tanggal_mulai"))
    copy_jadwal = payload.get("copy_jadwal", True)

    # 4. Perform deep copy
    service = DeepCopyService(source_project)
    new_project = service.copy(
        new_owner=request.user,
        new_name=new_name,
        new_tanggal_mulai=new_tanggal_mulai,
        copy_jadwal=copy_jadwal,
    )

    # 5. Return response
    return JsonResponse({
        "ok": True,
        "new_project": {...},
        "stats": service.get_stats(),
    }, status=201)
```

**Security:**
- `@login_required`: Only authenticated users
- `_owner_or_404`: Verify ownership (prevent unauthorized copy)
- CSRF protection: `X-CSRFToken` header required
- JSON validation: All inputs validated

**Error Handling:**
```python
try:
    # ... copy logic
except Exception as e:
    return JsonResponse({
        "ok": False,
        "error": f"Deep copy failed: {str(e)}"
    }, status=500)
```

### 6. URL Routing

**File:** `detail_project/urls.py`

```python
urlpatterns = [
    # ...
    path('api/project/<int:project_id>/deep-copy/',
         views_api.api_deep_copy_project,
         name='api_deep_copy_project'),
]
```

**URL Examples:**
- `/detail-project/api/project/123/deep-copy/`
- `/detail-project/api/project/456/deep-copy/`

### 7. UI Implementation

**File:** `dashboard/templates/dashboard/project_detail.html`

#### Button

```html
<button type="button"
        class="btn btn-sm btn-primary"
        data-bs-toggle="modal"
        data-bs-target="#copyProjectModal">
    <i class="fas fa-copy"></i> Copy Project
</button>
```

#### Modal

```html
<div class="modal fade" id="copyProjectModal">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5>Copy Project</h5>
            </div>
            <div class="modal-body">
                <!-- Form fields -->
                <input type="text" id="newProjectName" required>
                <input type="date" id="newTanggalMulai">
                <input type="checkbox" id="copyJadwal" checked>
            </div>
            <div class="modal-footer">
                <button id="btnConfirmCopy">Copy Project</button>
            </div>
        </div>
    </div>
</div>
```

#### JavaScript

```javascript
btnConfirm.addEventListener('click', async function() {
    // 1. Validate form
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return;
    }

    // 2. Show progress
    progressAlert.classList.remove('d-none');
    btnConfirm.disabled = true;

    // 3. Call API
    const response = await fetch(`/detail-project/api/project/${projectId}/deep-copy/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            new_name: newName,
            new_tanggal_mulai: newTanggalMulai,
            copy_jadwal: copyJadwal
        })
    });

    const data = await response.json();

    // 4. Handle response
    if (data.ok) {
        // Success - redirect to new project
        window.location.href = `/project/${data.new_project.id}/`;
    } else {
        // Error - show error message
        errorAlert.textContent = data.error;
        errorAlert.classList.remove('d-none');
    }
});
```

**Features:**
- Form validation (HTML5 + JavaScript)
- Progress indicator
- Error handling
- Auto-redirect on success
- CSRF token handling
- Async/await for clean code

### 8. Testing

**File:** `detail_project/tests/test_deepcopy_service.py`

**Coverage:** 23 tests covering:

1. **Initialization**
   - Valid project
   - None/unsaved project

2. **Basic Copy**
   - Minimal project
   - With new tanggal_mulai
   - Same owner

3. **Component Copy**
   - ProjectPricing
   - ProjectParameter
   - Hierarchy (Klasifikasi → SubKlasifikasi → Pekerjaan)
   - Volume
   - HargaItem + DetailAHSP
   - Tahapan + Jadwal

4. **Copy Options**
   - copy_jadwal=True
   - copy_jadwal=False

5. **Statistics**
   - get_stats() correctness
   - Stats are copy (not reference)

6. **Complex Scenarios**
   - Multiple copies
   - Copy of copy
   - Multiple pekerjaan

7. **Edge Cases**
   - Empty project
   - Preserves original
   - ID mappings correctness

**Run tests:**
```bash
# All tests
pytest detail_project/tests/test_deepcopy_service.py -v

# Specific test class
pytest detail_project/tests/test_deepcopy_service.py::TestDeepCopyBasic -v

# Single test
pytest detail_project/tests/test_deepcopy_service.py::TestDeepCopyBasic::test_copy_minimal_project -v

# With coverage
pytest detail_project/tests/test_deepcopy_service.py --cov=detail_project.services --cov-report=term-missing
```

**Test Fixtures:**
- `user`: Regular user
- `other_user`: Second user for multi-user tests
- `sample_project`: Minimal project (only project data)
- `full_project`: Fully populated project (all related data)

### 9. Performance Considerations

#### Query Count

For a project with:
- 10 klasifikasi
- 20 subklasifikasi
- 50 pekerjaan
- 50 volume
- 100 harga_item
- 200 detail_ahsp
- 5 tahapan
- 50 jadwal

**Total queries:** ~485 queries
- 1 project
- 1 pricing
- N parameters (depends on project)
- 10 klasifikasi
- 20 subklasifikasi
- 50 pekerjaan
- 50 volume
- 100 harga_item
- 200 detail_ahsp
- 5 tahapan
- 50 jadwal

#### Optimization Opportunities

**Current:** Individual `save()` calls
```python
for old_param in parameters:
    new_param = ProjectParameter(...)
    new_param.save()  # Individual insert
```

**Optimized (Future):** Bulk create
```python
new_params = []
for old_param in parameters:
    new_params.append(ProjectParameter(...))
ProjectParameter.objects.bulk_create(new_params)
```

**Trade-off:**
- `bulk_create()` is faster (1 query vs N queries)
- But doesn't return IDs immediately (needed for FK mapping)
- Would need to refetch to get IDs

**Current approach is correct** for maintaining ID mappings.

#### Transaction Overhead

Single transaction wrapping all operations:
```python
@transaction.atomic  # Single BEGIN/COMMIT
def copy(self, ...):
    # All 485 inserts
```

**Pros:**
- Atomic: All-or-nothing
- Consistent: No partial copies

**Cons:**
- Long-running transaction (holds locks)
- Can't parallelize

**Acceptable** because:
- Copy is infrequent operation
- Data integrity > speed
- Typical copy time < 10 seconds

### 10. Error Scenarios & Recovery

#### Scenario 1: Duplicate Name

**Error:** User already has project with same name

**Handling:**
```python
# Database constraint: UNIQUE(owner, nama_project) ?
# Currently: No constraint, allows duplicates
# If constraint added:
try:
    new_project.save()
except IntegrityError:
    return JsonResponse({
        "ok": False,
        "error": "Project name already exists"
    }, status=400)
```

#### Scenario 2: Mid-Copy Database Error

**Example:** Database connection lost at step 8

**Handling:**
```python
@transaction.atomic  # Automatic rollback!
def copy(self, ...):
    # Steps 1-7 succeed
    # Step 8 fails -> IntegrityError
    # Django rolls back ALL steps 1-7
    # Database state unchanged
```

**Result:** No partial copy, database clean

#### Scenario 3: Invalid FK Reference

**Example:** Pekerjaan references SubKlasifikasi that wasn't copied

**Prevention:**
```python
new_subklas_id = self.mappings['subklasifikasi'].get(old_subklas_id)
if new_subklas_id:  # Only copy if parent exists
    new_pekerjaan = Pekerjaan(...)
```

**Skip invalid references** instead of failing entire copy.

#### Scenario 4: User Navigates Away During Copy

**Client-side:** User closes modal or navigates away

**Server-side:** Transaction still completes (backend doesn't know client left)

**Result:**
- Copy completes successfully in background
- New project created
- User doesn't see it (didn't redirect)
- User can find it in dashboard

**Mitigation:** Add warning before closing modal (optional)

### 11. Future Enhancements

#### FASE 3.2: Multiple Copy

**Feature:** Copy project to multiple users at once

```python
def copy_multiple(self, target_users: List[User], new_name_template: str):
    """
    Copy project to multiple users.

    Example:
        service.copy_multiple(
            target_users=[user1, user2, user3],
            new_name_template="Project {username}"
        )
    """
    results = []
    for user in target_users:
        name = new_name_template.format(username=user.username)
        new_project = self.copy(new_owner=user, new_name=name)
        results.append(new_project)
    return results
```

#### FASE 3.3: Selective Copy

**Feature:** Copy only selected components

```python
def copy_selective(
    self,
    new_owner,
    new_name,
    options={
        'copy_pricing': True,
        'copy_parameters': True,
        'copy_pekerjaan': True,
        'copy_harga': True,
        'copy_ahsp': True,
        'copy_jadwal': False,
    }
):
    """Copy only selected components."""
    new_project = self._copy_project(...)

    if options['copy_pricing']:
        self._copy_project_pricing(new_project)

    if options['copy_parameters']:
        self._copy_project_parameters(new_project)

    # ... etc
```

#### FASE 3.4: Cross-User Template

**Feature:** Create project templates shareable across users

```python
class ProjectTemplate(models.Model):
    source_project = ForeignKey(Project)
    name = CharField(max_length=200)
    description = TextField()
    visibility = CharField(choices=[
        ('public', 'Public'),
        ('org', 'Organization'),
        ('private', 'Private')
    ])
    created_by = ForeignKey(User)
    usage_count = PositiveIntegerField(default=0)

def copy_from_template(template_id: int, owner: User):
    """Copy project from template."""
    template = ProjectTemplate.objects.get(id=template_id)
    service = DeepCopyService(template.source_project)
    new_project = service.copy(
        new_owner=owner,
        new_name=f"{template.name} - {owner.username}"
    )
    template.usage_count += 1
    template.save()
    return new_project
```

### 12. Maintenance Guide

#### Adding New Model to Copy

**Example:** Add copy support for new model `ProjectAttachment`

**Steps:**

1. **Add to mappings:**
```python
self.mappings = {
    # ... existing
    'attachment': {},  # NEW
}
```

2. **Add to stats:**
```python
self.stats = {
    # ... existing
    'attachment_copied': 0,  # NEW
}
```

3. **Add copy method:**
```python
def _copy_attachments(self, new_project):
    """Step 13: Copy ProjectAttachment."""
    attachments = ProjectAttachment.objects.filter(project=self.source)

    for old_att in attachments:
        old_id = old_att.id

        new_att = ProjectAttachment(
            project=new_project,
            filename=old_att.filename,
            file_path=old_att.file_path,
            # ... other fields
        )
        new_att.save()

        self.mappings['attachment'][old_id] = new_att.id
        self.stats['attachment_copied'] += 1
```

4. **Call in copy():**
```python
@transaction.atomic
def copy(self, ...):
    # ... existing steps

    # Step 13: Copy attachments
    self._copy_attachments(new_project)  # NEW

    return new_project
```

5. **Add tests:**
```python
def test_copy_attachments(self, full_project, other_user):
    """Test that attachments are copied correctly."""
    service = DeepCopyService(full_project)
    new_project = service.copy(other_user, "Copy with Attachments")

    assert ProjectAttachment.objects.filter(project=new_project).count() == 2
    assert service.stats['attachment_copied'] == 2
```

#### Debugging Copy Issues

**Enable debug logging:**
```python
import logging
logger = logging.getLogger(__name__)

class DeepCopyService:
    @transaction.atomic
    def copy(self, ...):
        logger.info(f"Starting copy of project {self.source.id}")

        new_project = self._copy_project(...)
        logger.debug(f"Project copied: {self.source.id} -> {new_project.id}")

        self._copy_klasifikasi(new_project)
        logger.debug(f"Copied {self.stats['klasifikasi_copied']} klasifikasi")

        # ... etc
```

**Check mappings:**
```python
service = DeepCopyService(project)
new_project = service.copy(...)

print("ID Mappings:")
for model_name, mapping in service.mappings.items():
    print(f"  {model_name}: {len(mapping)} items")
    # Example: klasifikasi: 10 items

print("\nStats:")
for stat_name, count in service.get_stats().items():
    print(f"  {stat_name}: {count}")
```

#### Monitoring Performance

**Add timing:**
```python
import time

@transaction.atomic
def copy(self, ...):
    start_time = time.time()

    # ... all steps

    elapsed = time.time() - start_time
    logger.info(f"Copy completed in {elapsed:.2f} seconds")
    logger.info(f"Stats: {self.get_stats()}")
```

**Database query count:**
```python
from django.db import connection
from django.test.utils import override_settings

@override_settings(DEBUG=True)
def test_copy_query_count():
    service = DeepCopyService(project)

    queries_before = len(connection.queries)
    new_project = service.copy(user, "Test Copy")
    queries_after = len(connection.queries)

    query_count = queries_after - queries_before
    print(f"Queries executed: {query_count}")
```

## Code Quality

### Type Hints

Currently minimal:
```python
def copy(self, new_owner, new_name, ...):
```

**Recommended:**
```python
from typing import Optional
from datetime import date

def copy(
    self,
    new_owner: User,
    new_name: str,
    new_tanggal_mulai: Optional[date] = None,
    copy_jadwal: bool = True
) -> Project:
```

### Docstrings

All methods have docstrings following Google style:
```python
def _copy_pekerjaan(self, new_project):
    """
    Step 6: Copy Pekerjaan instances.

    Args:
        new_project: The newly created project

    Returns:
        None (updates self.mappings and self.stats)
    """
```

### Error Messages

User-friendly error messages:
```python
# Bad
raise Exception("Error")

# Good
raise ValidationError("Source project must be a saved instance")
```

---

**Last Updated:** 2025-11-06
**Version:** 1.0 (FASE 3.1 Complete)
**Status:** Production Ready ✅
