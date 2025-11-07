# Usage Examples - P0/P1 Improvements

This document provides examples of using the new API helpers and loading manager improvements.

---

## 🔐 API Rate Limiting & Standardized Responses

### Backend: Using API Helpers

#### Example 1: Simple API Endpoint with Rate Limiting

```python
# detail_project/views_api.py
from .api_helpers import api_endpoint, APIResponse

@api_endpoint(max_requests=10, window=60)  # 10 requests per minute
@require_POST
def api_save_volume(request, project_id):
    """Save volume data with automatic rate limiting and authentication"""
    try:
        project = _owner_or_404(project_id, request.user)

        # Parse input
        data = json.loads(request.body)

        # Validate
        if not data.get('volumes'):
            return APIResponse.validation_error(
                message='Data volume tidak valid',
                field_errors={'volumes': 'Wajib diisi'}
            )

        # Process data
        with transaction.atomic():
            # ... save logic
            pass

        # Return success
        return APIResponse.success(
            data={'count': len(data['volumes'])},
            message='Volume berhasil disimpan'
        )

    except ValidationError as e:
        return APIResponse.validation_error(str(e))
    except Exception as e:
        return APIResponse.server_error(
            message='Gagal menyimpan volume',
            exception=e
        )
```

#### Example 2: Custom Rate Limiting

```python
from .api_helpers import rate_limit, APIResponse

@rate_limit(max_requests=5, window=300)  # 5 requests per 5 minutes
@login_required
@require_POST
def api_expensive_operation(request, project_id):
    """Expensive operation with stricter rate limiting"""
    # ... implementation
    return APIResponse.success(message='Operasi selesai')
```

#### Example 3: Different Response Types

```python
from .api_helpers import APIResponse

# Success with data
return APIResponse.success(
    data={'items': [1, 2, 3]},
    message='Data berhasil dimuat'
)

# Validation error with field details
return APIResponse.validation_error(
    message='Input tidak valid',
    field_errors={
        'nama': 'Nama wajib diisi',
        'email': 'Format email salah'
    }
)

# Not found
return APIResponse.not_found('Project tidak ditemukan')

# Forbidden
return APIResponse.forbidden('Anda tidak memiliki akses')

# Server error (with automatic logging)
return APIResponse.server_error(
    message='Terjadi kesalahan',
    exception=exc
)
```

#### Example 4: Transaction Safety

```python
from django.db import transaction
from .api_helpers import APIResponse

@api_endpoint(max_requests=20, window=60)
@require_POST
def api_upsert_pekerjaan(request, project_id):
    """Save with transaction safety"""
    try:
        project = _owner_or_404(project_id, request.user)

        # Lock project to prevent race conditions
        with transaction.atomic():
            project = Project.objects.select_for_update().get(id=project_id)

            # Parse data
            data = json.loads(request.body)

            # Validate all data before saving anything
            errors = validate_all_data(data)
            if errors:
                return APIResponse.validation_error(
                    message='Data tidak valid',
                    field_errors=errors
                )

            # Save everything (atomic - all or nothing)
            save_klasifikasi(project, data['klasifikasi'])
            save_subklasifikasi(project, data['subklasifikasi'])
            save_pekerjaan(project, data['pekerjaan'])

            # Invalidate cache
            invalidate_rekap_cache(project)

        return APIResponse.success(message='Data berhasil disimpan')

    except IntegrityError as e:
        # Transaction will auto-rollback
        logger.error(f"Integrity error: {e}", exc_info=True)
        return APIResponse.error(
            message='Terjadi konflik data',
            code='INTEGRITY_ERROR',
            status=409
        )
    except Exception as e:
        # Transaction will auto-rollback
        return APIResponse.server_error(exception=e)
```

---

## 🔄 Frontend: Loading States

### Example 1: Simple Loading Overlay

```javascript
// Import loading manager
import LoadingManager from '/static/detail_project/js/core/loading.js';

// Show loading
LoadingManager.show('Menyimpan data...');

try {
    const response = await fetch('/api/save/', {
        method: 'POST',
        body: JSON.stringify(data)
    });

    const result = await response.json();

    if (result.ok) {
        toast.success(result.message || 'Berhasil');
    } else {
        toast.error(result.error.message || 'Gagal');
    }
} catch (error) {
    toast.error('Terjadi kesalahan: ' + error.message);
} finally {
    LoadingManager.hide();
}
```

### Example 2: Using wrap() for Cleaner Code

```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

async function saveData(data) {
    // Wrap automatically shows/hides loading
    const result = await LoadingManager.wrap(
        fetch('/api/save/', {
            method: 'POST',
            body: JSON.stringify(data)
        }).then(r => r.json()),
        'Menyimpan data...'
    );

    if (result.ok) {
        toast.success(result.message);
    } else {
        toast.error(result.error.message);
    }
}
```

### Example 3: Progress Tracking

```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

async function uploadFiles(files) {
    // Show progress bar
    LoadingManager.showProgress('Mengupload file...', 0, files.length);

    for (let i = 0; i < files.length; i++) {
        await uploadFile(files[i]);

        // Update progress
        LoadingManager.updateProgress(i + 1, files.length);
    }

    LoadingManager.hide();
    toast.success('Semua file berhasil diupload');
}
```

### Example 4: Inline Loading (Button State)

```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

const button = document.getElementById('save-btn');

button.addEventListener('click', async (e) => {
    e.preventDefault();

    // Show inline loading
    const hideLoading = LoadingManager.showInline(button, 'Menyimpan...');

    try {
        await saveData();
        toast.success('Data tersimpan');
    } catch (error) {
        toast.error('Gagal menyimpan');
    } finally {
        hideLoading();
    }
});
```

### Example 5: Auto Button Loading

```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

const saveButton = document.getElementById('save-btn');

// Automatically handle loading state
LoadingManager.withButton(saveButton, async () => {
    await saveData();
    toast.success('Tersimpan');
}, 'Menyimpan...');
```

### Example 6: Update Loading Message

```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

LoadingManager.show('Memproses data...');

// Later, update message
await processStep1();
LoadingManager.updateMessage('Menyimpan ke database...');

await processStep2();
LoadingManager.updateMessage('Memperbarui cache...');

await processStep3();
LoadingManager.hide();
```

---

## 🎯 Complete Example: Save Pekerjaan Flow

### Backend (views_api.py)

```python
from django.db import transaction
from .api_helpers import api_endpoint, APIResponse, validate_required_fields
from .services import invalidate_rekap_cache

@api_endpoint(max_requests=20, window=60)
@require_POST
def api_save_pekerjaan_improved(request, project_id):
    """
    Save pekerjaan with full error handling and transaction safety.

    Rate Limited: 20 requests per minute per user
    """
    try:
        # 1. Authentication & Authorization
        project = _owner_or_404(project_id, request.user)

        # 2. Parse Input
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return APIResponse.validation_error(
                message='Format JSON tidak valid'
            )

        # 3. Validate Required Fields
        is_valid, error = validate_required_fields(
            data,
            ['klasifikasi', 'pekerjaan']
        )
        if not is_valid:
            return APIResponse.validation_error(error)

        # 4. Atomic Transaction with Lock
        with transaction.atomic():
            # Lock project to prevent concurrent modifications
            project = Project.objects.select_for_update().get(id=project_id)

            # Validate all data before any DB writes
            validation_errors = validate_all_pekerjaan(data)
            if validation_errors:
                return APIResponse.validation_error(
                    message='Data tidak valid',
                    field_errors=validation_errors
                )

            # Save data (all or nothing)
            stats = save_all_pekerjaan(project, data)

            # Invalidate related caches
            invalidate_rekap_cache(project)

        # 5. Success Response
        return APIResponse.success(
            data={
                'saved_count': stats['saved'],
                'project_id': project.id
            },
            message=f"{stats['saved']} pekerjaan berhasil disimpan"
        )

    except IntegrityError as e:
        logger.error(f"Integrity error saving pekerjaan: {e}", exc_info=True)
        return APIResponse.error(
            message='Terjadi konflik data. Silakan refresh dan coba lagi.',
            code='INTEGRITY_ERROR',
            status=409
        )

    except ValidationError as e:
        return APIResponse.validation_error(str(e))

    except Exception as e:
        logger.exception(f"Unexpected error saving pekerjaan: {e}")
        return APIResponse.server_error(
            message='Gagal menyimpan data pekerjaan',
            exception=e
        )
```

### Frontend (list_pekerjaan.js)

```javascript
// Import utilities
import LoadingManager from '/static/detail_project/js/core/loading.js';
import { jfetch } from '/static/detail_project/js/core/http.js';
import { toast } from '/static/detail_project/js/core/toast.js';

/**
 * Save pekerjaan data with loading state
 */
async function savePekerjaan(projectId, data) {
    // Wrap entire operation in loading
    const result = await LoadingManager.wrap(
        // API call
        jfetch(`/api/project/${projectId}/save-pekerjaan/`, {
            method: 'POST',
            body: JSON.stringify(data)
        }),
        // Loading message
        'Menyimpan data pekerjaan...'
    );

    // Handle response (standardized format)
    if (result.ok) {
        toast.success(result.message || 'Data berhasil disimpan');

        // Optionally show saved count
        if (result.data?.saved_count) {
            console.log(`Saved ${result.data.saved_count} items`);
        }

        return true;
    } else {
        // Handle different error types
        const error = result.error;

        if (error.code === 'VALIDATION_ERROR' && error.details?.fields) {
            // Show field-specific errors
            showFieldErrors(error.details.fields);
        } else if (error.code === 'RATE_LIMIT_EXCEEDED') {
            toast.warning('Terlalu banyak permintaan. Tunggu sebentar...');
        } else {
            toast.error(error.message || 'Gagal menyimpan data');
        }

        return false;
    }
}

/**
 * Save button with auto loading state
 */
document.getElementById('btn-save').addEventListener('click', async (e) => {
    e.preventDefault();

    // Collect form data
    const data = collectFormData();

    // Validate locally first (fast feedback)
    const errors = validateLocally(data);
    if (errors.length > 0) {
        toast.error('Silakan lengkapi data terlebih dahulu');
        return;
    }

    // Save with loading (handled automatically)
    const success = await savePekerjaan(PROJECT_ID, data);

    if (success) {
        // Optionally refresh UI
        await refreshPekerjaanList();
    }
});
```

---

## ✅ Migration Guide

### For Existing Endpoints

#### Before (Old Style):
```python
@login_required
@require_POST
def api_save_data(request, project_id):
    try:
        data = json.loads(request.body)
        # ... save logic
        return JsonResponse({'ok': True, 'message': 'Saved'})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)
```

#### After (New Style):
```python
from .api_helpers import api_endpoint, APIResponse

@api_endpoint(max_requests=30, window=60)
@require_POST
def api_save_data(request, project_id):
    try:
        project = _owner_or_404(project_id, request.user)

        data = json.loads(request.body)

        with transaction.atomic():
            # ... save logic
            pass

        return APIResponse.success(message='Saved')
    except Exception as e:
        return APIResponse.server_error(exception=e)
```

### For Existing Frontend Code

#### Before:
```javascript
async function save() {
    const response = await fetch('/api/save/', {method: 'POST', body: data});
    const result = await response.json();
    if (result.ok) alert('Saved');
}
```

#### After:
```javascript
import LoadingManager from '/static/detail_project/js/core/loading.js';

async function save() {
    const result = await LoadingManager.wrap(
        fetch('/api/save/', {method: 'POST', body: data}).then(r => r.json()),
        'Saving...'
    );
    if (result.ok) toast.success(result.message);
}
```

---

## 📊 Benefits Summary

### P0 (Critical) Fixes:

1. **API Rate Limiting** ✅
   - Prevents abuse and DoS attacks
   - Per-user, per-endpoint tracking
   - Configurable limits

2. **Transaction Safety** ✅
   - All-or-nothing saves
   - Project locking prevents race conditions
   - Automatic rollback on errors

3. **Query Optimization** ✅
   - N+1 queries eliminated where possible
   - Proper use of select_related/prefetch_related
   - Efficient aggregation

### P1 (High Priority) Improvements:

4. **Standardized API Responses** ✅
   - Consistent error format
   - Proper HTTP status codes
   - Structured error details

5. **Loading States** ✅
   - Global loading overlays
   - Progress tracking
   - Inline button states
   - Better UX feedback

---

## 🔧 Testing Recommendations

### Backend Tests:
```python
def test_rate_limiting():
    """Test that rate limiting works"""
    for i in range(11):  # Exceed limit of 10
        response = client.post('/api/save/')
    assert response.status_code == 429  # Too Many Requests

def test_transaction_rollback():
    """Test that errors rollback properly"""
    # Create invalid data
    with pytest.raises(IntegrityError):
        api_save_data(request, project_id)

    # Verify nothing was saved
    assert Pekerjaan.objects.count() == 0
```

### Frontend Tests:
```javascript
test('Loading manager shows and hides', async () => {
    LoadingManager.show('Test');
    expect(document.getElementById('dp-loading-overlay')).toBeTruthy();

    LoadingManager.hide();
    await new Promise(r => setTimeout(r, 400)); // Wait for animation
    expect(document.getElementById('dp-loading-overlay')).toBeFalsy();
});
```

---

## 📚 Further Reading

- Django Transaction Docs: https://docs.djangoproject.com/en/stable/topics/db/transactions/
- Django Cache Framework: https://docs.djangoproject.com/en/stable/topics/cache/
- HTTP Status Codes: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
- Rate Limiting Best Practices: https://cloud.google.com/architecture/rate-limiting-strategies
