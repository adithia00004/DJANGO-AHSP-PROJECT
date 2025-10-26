# detail_project/views_api_tahapan.py
# NEW FILE: API endpoints untuk Tahapan Pelaksanaan

import json
from django.db import models  # ADD THIS if not present
from decimal import Decimal, InvalidOperation
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods, require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from django.db.models import Sum, Max


from .models import (
    Pekerjaan,
    TahapPelaksanaan, 
    PekerjaanTahapan
)
from .services import (
    compute_kebutuhan_items,
    get_tahapan_summary,
    get_unassigned_pekerjaan
)

# Helper untuk validasi ownership
def _owner_or_404(project_id, user):
    """Get project atau 404 jika bukan owner"""
    from dashboard.models import Project
    project = get_object_or_404(Project, id=project_id)
    if project.owner != user:
        from django.http import Http404
        raise Http404("Project not found")
    return project


# ============================================================================
# TAHAPAN CRUD
# ============================================================================

@login_required
@require_http_methods(['GET', 'POST'])
def api_list_create_tahapan(request, project_id):
    """
    GET: List semua tahapan untuk project
    POST: Create tahapan baru
    """
    project = _owner_or_404(project_id, request.user)

    # Helper function untuk serialize date
    def serialize_date(date_field):
        """Convert date field to string safely"""
        if not date_field:
            return None
        if hasattr(date_field, 'isoformat'):
            return date_field.isoformat()
        return str(date_field)

    if request.method == 'GET':
        # Return list tahapan dengan summary
        summary = get_tahapan_summary(project)
        
        return JsonResponse({
            'ok': True,
            'tahapan': summary,
            'count': len(summary)
        })

    # POST: Create new tahapan
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        nama = data.get('nama', '').strip()
        if not nama:
            return JsonResponse({
                'ok': False,
                'error': 'Nama tahapan harus diisi'
            }, status=400)
        
        # Check duplicate nama
        if TahapPelaksanaan.objects.filter(project=project, nama=nama).exists():
            return JsonResponse({
                'ok': False,
                'error': f'Tahapan dengan nama "{nama}" sudah ada'
            }, status=400)
        
        # Get max urutan untuk auto-increment
        max_urutan_result = TahapPelaksanaan.objects.filter(
            project=project
        ).aggregate(max_urutan=models.Max('urutan'))
        
        max_urutan = max_urutan_result['max_urutan']
        if max_urutan is None:
            max_urutan = 0
        
        # Get urutan from request or auto-increment
        urutan = data.get('urutan')
        if urutan is None:
            urutan = max_urutan + 1
        else:
            urutan = int(urutan)
        
        # Create tahapan
        tahap = TahapPelaksanaan.objects.create(
            project=project,
            nama=nama,
            urutan=urutan,
            deskripsi=data.get('deskripsi', ''),
            tanggal_mulai=data.get('tanggal_mulai') or None,
            tanggal_selesai=data.get('tanggal_selesai') or None
        )

        tahap.refresh_from_db()  
        
        return JsonResponse({
            'ok': True,
            'tahapan': {
                'tahapan_id': tahap.id,
                'nama': tahap.nama,
                'urutan': tahap.urutan,
                'deskripsi': tahap.deskripsi,
                'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
                'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except ValidationError as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=400)
    except Exception as e:
        # Log the actual error for debugging
        import traceback
        print("Error creating tahapan:", str(e))
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_http_methods(['GET', 'PUT', 'DELETE'])
def api_update_delete_tahapan(request, project_id, tahapan_id):
    """
    GET: Get detail tahapan
    PUT: Update tahapan
    DELETE: Delete tahapan
    """
    project = _owner_or_404(project_id, request.user)
    tahap = get_object_or_404(TahapPelaksanaan, id=tahapan_id, project=project)
    
    if request.method == 'GET':
        # Get detail dengan pekerjaan list
        pekerjaan_list = [
            {
                'pekerjaan_id': pt.pekerjaan_id,
                'kode': pt.pekerjaan.snapshot_kode,
                'uraian': pt.pekerjaan.snapshot_uraian,
                'proporsi': float(pt.proporsi_volume),
                'volume_efektif': float(pt.volume_efektif),
                'catatan': pt.catatan
            }
            for pt in tahap.pekerjaan_items.select_related('pekerjaan').order_by('pekerjaan__ordering_index')
        ]
        
        return JsonResponse({
            'ok': True,
            'tahapan': {
                'tahapan_id': tahap.id,
                'nama': tahap.nama,
                'urutan': tahap.urutan,
                'deskripsi': tahap.deskripsi,
                'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
                'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
                'jumlah_pekerjaan': len(pekerjaan_list),
                'pekerjaan': pekerjaan_list
            }
        })
    
    elif request.method == 'PUT':
        # Update tahapan
        try:
            data = json.loads(request.body)
            
            # Update fields
            if 'nama' in data:
                new_nama = data['nama'].strip()
                if new_nama:
                    # Check duplicate (exclude self)
                    if TahapPelaksanaan.objects.filter(
                        project=project, nama=new_nama
                    ).exclude(id=tahap.id).exists():
                        return JsonResponse({
                            'ok': False,
                            'error': f'Tahapan dengan nama "{new_nama}" sudah ada'
                        }, status=400)
                    tahap.nama = new_nama
            
            if 'urutan' in data:
                tahap.urutan = int(data['urutan'])
            
            if 'deskripsi' in data:
                tahap.deskripsi = data['deskripsi']
            
            if 'tanggal_mulai' in data:
                tahap.tanggal_mulai = data['tanggal_mulai'] or None
            
            if 'tanggal_selesai' in data:
                tahap.tanggal_selesai = data['tanggal_selesai'] or None
            
            tahap.save()
            
            return JsonResponse({
                'ok': True,
                'message': 'Tahapan berhasil diupdate',
                'tahapan': {
                    'tahapan_id': tahap.id,
                    'nama': tahap.nama,
                    'urutan': tahap.urutan,
                    'deskripsi': tahap.deskripsi,
                    'tanggal_mulai': tahap.tanggal_mulai.isoformat() if tahap.tanggal_mulai else None,
                    'tanggal_selesai': tahap.tanggal_selesai.isoformat() if tahap.tanggal_selesai else None,
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
        except ValidationError as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'ok': False, 'error': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        # Delete tahapan
        # Check if ada assignments
        if tahap.pekerjaan_items.exists():
            return JsonResponse({
                'ok': False,
                'error': 'Tidak dapat menghapus tahapan yang masih memiliki pekerjaan. Hapus assignment terlebih dahulu.'
            }, status=400)
        
        tahap_nama = tahap.nama
        tahap.delete()
        
        return JsonResponse({
            'ok': True,
            'message': f'Tahapan "{tahap_nama}" berhasil dihapus'
        })


@login_required
@require_POST
def api_reorder_tahapan(request, project_id):
    """
    Reorder tahapan (bulk update urutan)
    
    Body: {"tahapan_order": [id1, id2, id3, ...]}
    """
    project = _owner_or_404(project_id, request.user)
    
    try:
        data = json.loads(request.body)
        tahapan_order = data.get('tahapan_order', [])
        
        if not isinstance(tahapan_order, list):
            return JsonResponse({
                'ok': False,
                'error': 'tahapan_order harus berupa array'
            }, status=400)
        
        # Update urutan
        with transaction.atomic():
            for idx, tahapan_id in enumerate(tahapan_order):
                TahapPelaksanaan.objects.filter(
                    id=tahapan_id,
                    project=project
                ).update(urutan=idx)
        
        return JsonResponse({
            'ok': True,
            'message': 'Urutan tahapan berhasil diupdate'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


# ============================================================================
# ASSIGNMENT MANAGEMENT
# ============================================================================

@login_required
@require_POST
@transaction.atomic
def api_assign_pekerjaan_to_tahapan(request, project_id, tahapan_id):
    """
    Assign pekerjaan ke tahapan dengan proporsi.
    
    Body: {
        "assignments": [
            {
                "pekerjaan_id": 1,
                "proporsi": 60.00,
                "catatan": "optional"
            },
            {
                "pekerjaan_id": 2,
                "proporsi": 100.00
            }
        ]
    }
    """
    project = _owner_or_404(project_id, request.user)
    tahap = get_object_or_404(TahapPelaksanaan, id=tahapan_id, project=project)
    
    try:
        data = json.loads(request.body)
        assignments = data.get('assignments', [])
        
        if not isinstance(assignments, list):
            return JsonResponse({
                'ok': False,
                'error': 'assignments harus berupa array'
            }, status=400)
        
        created_count = 0
        updated_count = 0
        errors = []
        
        for item in assignments:
            pekerjaan_id = item.get('pekerjaan_id')
            proporsi = item.get('proporsi')
            catatan = item.get('catatan', '')
            
            # Validation
            if not pekerjaan_id:
                errors.append({'error': 'pekerjaan_id required', 'item': item})
                continue
            
            if proporsi is None:
                errors.append({'error': 'proporsi required', 'item': item})
                continue
            
            try:
                proporsi_decimal = Decimal(str(proporsi))
                if proporsi_decimal < Decimal('0.01') or proporsi_decimal > Decimal('100'):
                    errors.append({
                        'error': f'Proporsi harus 0.01-100, got {proporsi}',
                        'pekerjaan_id': pekerjaan_id
                    })
                    continue
            except (InvalidOperation, ValueError):
                errors.append({
                    'error': f'Invalid proporsi: {proporsi}',
                    'pekerjaan_id': pekerjaan_id
                })
                continue
            
            # Get pekerjaan
            try:
                pekerjaan = Pekerjaan.objects.get(id=pekerjaan_id, project=project)
            except Pekerjaan.DoesNotExist:
                errors.append({
                    'error': f'Pekerjaan {pekerjaan_id} not found',
                    'pekerjaan_id': pekerjaan_id
                })
                continue
            
            # Create or update assignment
            pt, created = PekerjaanTahapan.objects.update_or_create(
                pekerjaan=pekerjaan,
                tahapan=tahap,
                defaults={
                    'proporsi_volume': proporsi_decimal,
                    'catatan': catatan
                }
            )
            
            if created:
                created_count += 1
            else:
                updated_count += 1
        
        return JsonResponse({
            'ok': True if not errors else len(errors) < len(assignments),
            'created': created_count,
            'updated': updated_count,
            'errors': errors,
            'message': f'Berhasil assign {created_count} dan update {updated_count} pekerjaan'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def api_unassign_pekerjaan_from_tahapan(request, project_id, tahapan_id):
    """
    Unassign pekerjaan dari tahapan.
    
    Body: {"pekerjaan_ids": [1, 2, 3]}
    """
    project = _owner_or_404(project_id, request.user)
    tahap = get_object_or_404(TahapPelaksanaan, id=tahapan_id, project=project)
    
    try:
        data = json.loads(request.body)
        pekerjaan_ids = data.get('pekerjaan_ids', [])
        
        if not isinstance(pekerjaan_ids, list):
            return JsonResponse({
                'ok': False,
                'error': 'pekerjaan_ids harus berupa array'
            }, status=400)
        
        # Delete assignments
        deleted_count = PekerjaanTahapan.objects.filter(
            tahapan=tahap,
            pekerjaan_id__in=pekerjaan_ids
        ).delete()[0]
        
        return JsonResponse({
            'ok': True,
            'deleted': deleted_count,
            'message': f'Berhasil unassign {deleted_count} pekerjaan'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
@require_GET
def api_get_pekerjaan_assignments(request, project_id, pekerjaan_id):
    """
    Get all tahapan assignments untuk satu pekerjaan.
    
    Returns:
        {
            "ok": true,
            "pekerjaan": {...},
            "assignments": [...],
            "total_assigned": 60.00,
            "unassigned": 40.00,
            "is_fully_assigned": false
        }
    """
    project = _owner_or_404(project_id, request.user)
    pekerjaan = get_object_or_404(Pekerjaan, id=pekerjaan_id, project=project)
    
    # Get assignments
    assignments = PekerjaanTahapan.objects.filter(
        pekerjaan=pekerjaan
    ).select_related('tahapan').order_by('tahapan__urutan')
    
    total_assigned = sum(a.proporsi_volume for a in assignments)
    unassigned = Decimal('100') - total_assigned
    
    return JsonResponse({
        'ok': True,
        'pekerjaan': {
            'pekerjaan_id': pekerjaan.id,
            'kode': pekerjaan.snapshot_kode,
            'uraian': pekerjaan.snapshot_uraian,
            'satuan': pekerjaan.snapshot_satuan
        },
        'assignments': [
            {
                'tahapan_id': a.tahapan_id,
                'tahapan_nama': a.tahapan.nama,
                'proporsi': float(a.proporsi_volume),
                'volume_efektif': float(a.volume_efektif),
                'catatan': a.catatan
            }
            for a in assignments
        ],
        'total_assigned': float(total_assigned),
        'unassigned': float(unassigned),
        'is_fully_assigned': abs(float(unassigned)) < 0.01
    })


# ============================================================================
# VALIDATION & STATUS
# ============================================================================

@login_required
@require_GET
def api_validate_all_assignments(request, project_id):
    """
    Validate all assignments in project.
    Check for incomplete assignments, etc.
    """
    project = _owner_or_404(project_id, request.user)
    
    unassigned = get_unassigned_pekerjaan(project)
    
    total_pekerjaan = Pekerjaan.objects.filter(project=project).count()
    fully_assigned = total_pekerjaan - len(unassigned)
    
    return JsonResponse({
        'ok': True,
        'total_pekerjaan': total_pekerjaan,
        'fully_assigned': fully_assigned,
        'incomplete': len(unassigned),
        'incomplete_list': unassigned,
        'is_complete': len(unassigned) == 0
    })


@login_required
@require_GET
def api_get_unassigned_pekerjaan(request, project_id):
    """
    Get list pekerjaan yang belum fully assigned.
    """
    project = _owner_or_404(project_id, request.user)
    
    unassigned = get_unassigned_pekerjaan(project)
    
    return JsonResponse({
        'ok': True,
        'count': len(unassigned),
        'pekerjaan': unassigned
    })


# ============================================================================
# REKAP KEBUTUHAN (ENHANCED)
# ============================================================================

@login_required
@require_GET
def api_get_rekap_kebutuhan_enhanced(request, project_id):
    """
    Enhanced rekap kebutuhan dengan support filtering.
    
    Query params:
        - mode: 'all' | 'tahapan'
        - tahapan_id: int (if mode=tahapan)
        - klasifikasi: comma-separated IDs
        - sub_klasifikasi: comma-separated IDs
        - kategori: comma-separated (TK,BHN,ALT,LAIN)
    
    Example:
        /api/project/1/rekap-kebutuhan/?mode=tahapan&tahapan_id=1
        /api/project/1/rekap-kebutuhan/?mode=all&klasifikasi=1,2&kategori=TK,BHN
    """
    project = _owner_or_404(project_id, request.user)
    
    # Parse query params
    mode = request.GET.get('mode', 'all')
    tahapan_id = request.GET.get('tahapan_id')
    
    # Build filters dict
    filters = {}
    
    # Klasifikasi filter
    if request.GET.get('klasifikasi'):
        try:
            klas_ids = [int(x.strip()) for x in request.GET.get('klasifikasi').split(',') if x.strip()]
            if klas_ids:
                filters['klasifikasi_ids'] = klas_ids
        except ValueError:
            pass
    
    # Sub-klasifikasi filter
    if request.GET.get('sub_klasifikasi'):
        try:
            sub_klas_ids = [int(x.strip()) for x in request.GET.get('sub_klasifikasi').split(',') if x.strip()]
            if sub_klas_ids:
                filters['sub_klasifikasi_ids'] = sub_klas_ids
        except ValueError:
            pass
    
    # Kategori item filter
    if request.GET.get('kategori'):
        kategori_list = [x.strip().upper() for x in request.GET.get('kategori').split(',') if x.strip()]
        valid_kat = [k for k in kategori_list if k in ('TK', 'BHN', 'ALT', 'LAIN')]
        if valid_kat:
            filters['kategori_items'] = valid_kat
    
    # Compute kebutuhan
    try:
        rows = compute_kebutuhan_items(
            project,
            mode=mode,
            tahapan_id=int(tahapan_id) if tahapan_id else None,
            filters=filters if filters else None
        )
    except Exception as e:
        return JsonResponse({
            'ok': False,
            'error': str(e)
        }, status=500)
    
    # Count per kategori
    counts = {"TK": 0, "BHN": 0, "ALT": 0, "LAIN": 0}
    for r in rows:
        k = r.get("kategori")
        if k in counts:
            counts[k] += 1
    
    # Meta info
    meta = {
        "counts_per_kategori": counts,
        "n_rows": len(rows),
        "mode": mode,
        "filters_applied": bool(filters),
        "generated_at": __import__('django.utils.timezone', fromlist=['now']).now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    
    if mode == 'tahapan' and tahapan_id:
        try:
            tahap = TahapPelaksanaan.objects.get(id=tahapan_id, project=project)
            meta['tahapan'] = {
                'tahapan_id': tahap.id,
                'nama': tahap.nama,
                'jumlah_pekerjaan': tahap.get_total_pekerjaan()
            }
        except TahapPelaksanaan.DoesNotExist:
            pass
    
    return JsonResponse({
        "ok": True,
        "rows": rows,
        "meta": meta
    })


# ============================================================================
# TIME SCALE MODE: TAHAPAN AUTO-GENERATION
# ============================================================================

@login_required
@require_POST
@transaction.atomic
def api_regenerate_tahapan(request, project_id):
    """
    Regenerate tahapan based on time scale mode.

    POST Body:
        {
            "mode": "daily" | "weekly" | "monthly" | "custom",
            "week_end_day": 0-6 (optional, default 0=Sunday for weekly mode),
            "convert_assignments": true | false (optional, default true)
        }

    Process:
        1. Delete old auto-generated tahapan (is_auto_generated=True)
        2. Generate new tahapan based on mode
        3. (Optional) Convert existing assignments to new tahapan

    Returns:
        {
            "ok": true,
            "mode": "weekly",
            "tahapan_created": 10,
            "tahapan_deleted": 8,
            "assignments_converted": 50,
            "tahapan": [...]
        }
    """
    from datetime import datetime, timedelta, date
    from decimal import Decimal

    project = _owner_or_404(project_id, request.user)

    try:
        data = json.loads(request.body)
        mode = data.get('mode', 'custom')
        week_end_day = data.get('week_end_day', 0)  # 0 = Sunday
        convert_assignments = data.get('convert_assignments', True)

        # Validate mode
        if mode not in ['daily', 'weekly', 'monthly', 'custom']:
            return JsonResponse({
                'ok': False,
                'error': 'Invalid mode. Must be: daily, weekly, monthly, or custom'
            }, status=400)

        # Validate project timeline
        if not project.tanggal_mulai or not project.tanggal_selesai:
            return JsonResponse({
                'ok': False,
                'error': 'Project timeline not set. Please set tanggal_mulai and tanggal_selesai first.'
            }, status=400)

        if project.tanggal_selesai < project.tanggal_mulai:
            return JsonResponse({
                'ok': False,
                'error': 'Invalid timeline: tanggal_selesai must be >= tanggal_mulai'
            }, status=400)

        # For custom mode, no generation needed - keep existing tahapan
        if mode == 'custom':
            existing_tahapan = TahapPelaksanaan.objects.filter(
                project=project
            ).order_by('urutan')

            return JsonResponse({
                'ok': True,
                'mode': 'custom',
                'message': 'Custom mode - using existing tahapan',
                'tahapan_count': existing_tahapan.count(),
                'tahapan': [
                    {
                        'tahapan_id': t.id,
                        'nama': t.nama,
                        'urutan': t.urutan,
                        'tanggal_mulai': t.tanggal_mulai.isoformat() if t.tanggal_mulai else None,
                        'tanggal_selesai': t.tanggal_selesai.isoformat() if t.tanggal_selesai else None,
                        'is_auto_generated': t.is_auto_generated,
                        'generation_mode': t.generation_mode
                    }
                    for t in existing_tahapan
                ]
            })

        # STEP 1: Backup old assignments (if conversion needed)
        old_assignments = []
        if convert_assignments:
            old_assignments = list(
                PekerjaanTahapan.objects.filter(
                    tahapan__project=project,
                    tahapan__is_auto_generated=True
                ).select_related('pekerjaan', 'tahapan').values(
                    'pekerjaan_id',
                    'tahapan__tanggal_mulai',
                    'tahapan__tanggal_selesai',
                    'proporsi_volume'
                )
            )

        # STEP 2: Delete old auto-generated tahapan
        deleted_count, _ = TahapPelaksanaan.objects.filter(
            project=project,
            is_auto_generated=True
        ).delete()

        # STEP 3: Generate new tahapan based on mode
        new_tahapan = []

        if mode == 'daily':
            new_tahapan = _generate_daily_tahapan(project)
        elif mode == 'weekly':
            new_tahapan = _generate_weekly_tahapan(project, week_end_day)
        elif mode == 'monthly':
            new_tahapan = _generate_monthly_tahapan(project)

        # Bulk create
        created_tahapan = TahapPelaksanaan.objects.bulk_create(new_tahapan)

        # STEP 4: Convert assignments (if requested)
        assignments_converted = 0
        if convert_assignments and old_assignments:
            # TODO: Implement assignment conversion in Phase 3.3
            # For now, skip conversion
            pass

        # Return response
        return JsonResponse({
            'ok': True,
            'mode': mode,
            'tahapan_deleted': deleted_count,
            'tahapan_created': len(created_tahapan),
            'assignments_converted': assignments_converted,
            'message': f'Successfully generated {len(created_tahapan)} tahapan for {mode} mode',
            'tahapan': [
                {
                    'tahapan_id': t.id,
                    'nama': t.nama,
                    'urutan': t.urutan,
                    'tanggal_mulai': t.tanggal_mulai.isoformat() if t.tanggal_mulai else None,
                    'tanggal_selesai': t.tanggal_selesai.isoformat() if t.tanggal_selesai else None,
                    'is_auto_generated': t.is_auto_generated,
                    'generation_mode': t.generation_mode
                }
                for t in created_tahapan
            ]
        })

    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


def _generate_daily_tahapan(project):
    """Generate one tahapan per day"""
    from datetime import timedelta

    tahapan_list = []
    current_date = project.tanggal_mulai
    day_num = 1

    while current_date <= project.tanggal_selesai:
        tahap = TahapPelaksanaan(
            project=project,
            nama=f"Day {day_num}",
            urutan=day_num - 1,
            tanggal_mulai=current_date,
            tanggal_selesai=current_date,
            is_auto_generated=True,
            generation_mode='daily'
        )
        tahapan_list.append(tahap)

        current_date += timedelta(days=1)
        day_num += 1

        # Safety limit
        if day_num > 1000:
            break

    return tahapan_list


def _generate_weekly_tahapan(project, week_end_day=0):
    """Generate one tahapan per week"""
    from datetime import timedelta

    tahapan_list = []
    current_start = project.tanggal_mulai
    week_num = 1

    while current_start <= project.tanggal_selesai:
        # Calculate week end
        days_until_week_end = (week_end_day - current_start.weekday() + 7) % 7

        if days_until_week_end == 0 and current_start.weekday() == week_end_day:
            current_end = current_start
        else:
            current_end = current_start + timedelta(days=days_until_week_end)

        # Don't exceed project end
        if current_end > project.tanggal_selesai:
            current_end = project.tanggal_selesai

        # Format label
        start_str = current_start.strftime("%d %b")
        end_str = current_end.strftime("%d %b")
        label = f"Week {week_num}: {start_str} - {end_str}"

        tahap = TahapPelaksanaan(
            project=project,
            nama=label,
            urutan=week_num - 1,
            tanggal_mulai=current_start,
            tanggal_selesai=current_end,
            is_auto_generated=True,
            generation_mode='weekly'
        )
        tahapan_list.append(tahap)

        # Move to next week
        current_start = current_end + timedelta(days=1)
        week_num += 1

        # Safety limit
        if week_num > 100:
            break

    return tahapan_list


def _generate_monthly_tahapan(project):
    """Generate one tahapan per month"""
    from datetime import date
    import calendar

    tahapan_list = []
    current_date = project.tanggal_mulai
    month_num = 1

    while current_date <= project.tanggal_selesai:
        # Month start is current_date
        month_start = current_date

        # Month end is last day of the month
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        month_end = date(current_date.year, current_date.month, last_day)

        # Don't exceed project end
        if month_end > project.tanggal_selesai:
            month_end = project.tanggal_selesai

        # Format label (Indonesian month names)
        month_names = {
            1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
            5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
            9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
        }
        month_name = month_names.get(current_date.month, str(current_date.month))
        label = f"{month_name} {current_date.year}"

        tahap = TahapPelaksanaan(
            project=project,
            nama=label,
            urutan=month_num - 1,
            tanggal_mulai=month_start,
            tanggal_selesai=month_end,
            is_auto_generated=True,
            generation_mode='monthly'
        )
        tahapan_list.append(tahap)

        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

        month_num += 1

        # Safety limit
        if month_num > 24:
            break

    return tahapan_list