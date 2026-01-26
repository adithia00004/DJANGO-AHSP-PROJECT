"""
Celery tasks for AHSP referensi app.

PHASE 5: Celery Async Tasks
PHASE 6: Export Tasks

Provides background tasks for:
- Async AHSP import
- Async export (Excel, PDF)
- Audit log cleanup
- Email notifications
- Cache warmup
- Periodic maintenance
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from datetime import timedelta

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


# =============================================================================
# ASYNC IMPORT TASKS
# =============================================================================

@shared_task(bind=True, name='referensi.tasks.async_import_ahsp')
def async_import_ahsp(self, file_path: str, sumber: str, user_id: int = None) -> Dict[str, Any]:
    """
    Async task to import AHSP from file.

    Args:
        file_path: Path to xlsx/xls file
        sumber: Source name for the import
        user_id: User ID who initiated the import

    Returns:
        dict: Import summary with counts and errors
    """
    from referensi.services.ahsp_parser import parse_ahsp
    from referensi.services.import_writer import write_parse_result_to_db
    from referensi.models import SecurityAuditLog

    # Update task state
    self.update_state(state='PROGRESS', meta={'status': 'Parsing file...'})

    try:
        # Parse file
        parse_result = parse_ahsp(file_path, sumber=sumber)

        if parse_result.errors:
            # Log errors
            logger.error(f"Import failed for {file_path}: {parse_result.errors}")

            # Create audit log
            if user_id:
                SecurityAuditLog.objects.create(
                    event_type=SecurityAuditLog.EVENT_IMPORT,
                    severity=SecurityAuditLog.SEVERITY_HIGH,
                    message=f"Import failed: {file_path}",
                    user_id=user_id,
                    metadata={'errors': parse_result.errors[:10]},  # First 10 errors
                )

            return {
                'status': 'error',
                'errors': parse_result.errors,
                'jobs_count': len(parse_result.jobs),
            }

        # Update task state
        self.update_state(state='PROGRESS', meta={'status': f'Writing {len(parse_result.jobs)} jobs to database...'})

        # Write to database
        summary = write_parse_result_to_db(parse_result, source_file=file_path)

        # Create audit log
        if user_id:
            SecurityAuditLog.objects.create(
                event_type=SecurityAuditLog.EVENT_IMPORT,
                severity=SecurityAuditLog.SEVERITY_INFO,
                message=f"Import completed: {summary.jobs_created} created, {summary.jobs_updated} updated",
                user_id=user_id,
                metadata={
                    'file': file_path,
                    'jobs_created': summary.jobs_created,
                    'jobs_updated': summary.jobs_updated,
                    'rincian_written': summary.rincian_written,
                },
            )

        logger.info(f"Import completed for {file_path}: {summary.jobs_created} created, {summary.jobs_updated} updated")

        return {
            'status': 'success',
            'jobs_created': summary.jobs_created,
            'jobs_updated': summary.jobs_updated,
            'rincian_written': summary.rincian_written,
            'detail_errors': summary.detail_errors[:10],  # First 10 errors
        }

    except Exception as exc:
        logger.exception(f"Unexpected error during import: {exc}")

        # Create audit log
        if user_id:
            SecurityAuditLog.objects.create(
                event_type=SecurityAuditLog.EVENT_IMPORT,
                severity=SecurityAuditLog.SEVERITY_CRITICAL,
                message=f"Import failed with exception: {str(exc)}",
                user_id=user_id,
                metadata={'error': str(exc), 'file': file_path},
            )

        raise


# =============================================================================
# AUDIT LOG TASKS
# =============================================================================

@shared_task(name='referensi.tasks.cleanup_audit_logs_task')
def cleanup_audit_logs_task(days: int = 90, keep_critical_days: int = 180) -> Dict[str, int]:
    """
    Cleanup old audit logs.

    Args:
        days: Delete non-critical logs older than this many days
        keep_critical_days: Delete critical logs older than this many days

    Returns:
        dict: Counts of deleted logs
    """
    from referensi.models import SecurityAuditLog

    cutoff_normal = timezone.now() - timedelta(days=days)
    cutoff_critical = timezone.now() - timedelta(days=keep_critical_days)

    # Delete non-critical old logs
    deleted_normal = SecurityAuditLog.objects.filter(
        timestamp__lt=cutoff_normal
    ).exclude(severity=SecurityAuditLog.SEVERITY_CRITICAL).delete()[0]

    # Delete very old critical logs
    deleted_critical = SecurityAuditLog.objects.filter(
        timestamp__lt=cutoff_critical,
        severity=SecurityAuditLog.SEVERITY_CRITICAL
    ).delete()[0]

    total_deleted = deleted_normal + deleted_critical

    logger.info(f"Cleaned up {total_deleted} audit logs ({deleted_normal} normal, {deleted_critical} critical)")

    return {
        'total_deleted': total_deleted,
        'normal_deleted': deleted_normal,
        'critical_deleted': deleted_critical,
    }


@shared_task(name='referensi.tasks.generate_audit_summary_task')
def generate_audit_summary_task(period: str = 'hourly') -> Dict[str, Any]:
    """
    Generate audit summary statistics.

    Args:
        period: Summary period ('hourly', 'daily', 'weekly', 'monthly')

    Returns:
        dict: Summary statistics
    """
    from referensi.models import SecurityAuditLog
    from django.db.models import Count

    if period == 'hourly':
        time_delta = timedelta(hours=1)
    elif period == 'daily':
        time_delta = timedelta(days=1)
    elif period == 'weekly':
        time_delta = timedelta(weeks=1)
    elif period == 'monthly':
        time_delta = timedelta(days=30)
    else:
        time_delta = timedelta(days=1)

    start_time = timezone.now() - time_delta

    # Get counts by severity
    summary = SecurityAuditLog.objects.filter(
        timestamp__gte=start_time
    ).values('severity').annotate(
        count=Count('id')
    )

    stats = {item['severity']: item['count'] for item in summary}

    logger.info(f"Generated {period} audit summary: {stats}")

    return {
        'period': period,
        'start_time': start_time.isoformat(),
        'stats': stats,
    }


@shared_task(name='referensi.tasks.send_audit_alerts_task')
def send_audit_alerts_task() -> Dict[str, Any]:
    """
    Send email alerts for critical audit events.

    Returns:
        dict: Alert counts and status
    """
    from referensi.models import SecurityAuditLog

    # Get critical/high events from last hour
    one_hour_ago = timezone.now() - timedelta(hours=1)

    critical_events = SecurityAuditLog.objects.filter(
        timestamp__gte=one_hour_ago,
        severity__in=[SecurityAuditLog.SEVERITY_CRITICAL, SecurityAuditLog.SEVERITY_HIGH],
        resolved=False  # Only unresolved events
    ).order_by('-timestamp')[:10]  # Max 10 per email

    if not critical_events:
        logger.info("No critical audit events to alert")
        return {'status': 'no_alerts', 'count': 0}

    # Build email content
    subject = f"[AHSP Security Alert] {critical_events.count()} Critical Events"

    body = f"""
AHSP Security Alert

{critical_events.count()} critical/high severity events detected in the last hour:

"""

    for event in critical_events:
        body += f"""
Event ID: {event.id}
Severity: {event.get_severity_display()}
Type: {event.get_event_type_display()}
Time: {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Message: {event.message}
User: {event.user.username if event.user else 'System'}
IP: {event.ip_address or 'N/A'}
---
"""

    body += f"""

Please review these events at: {settings.ALLOWED_HOSTS[0]}/referensi/audit/logs/

This is an automated alert from AHSP Security Monitoring.
"""

    # Send email
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=settings.AUDIT_ALERT_EMAIL_RECIPIENTS,
            fail_silently=False,
        )

        logger.info(f"Sent audit alert email for {critical_events.count()} events")

        return {
            'status': 'sent',
            'count': critical_events.count(),
            'recipients': len(settings.AUDIT_ALERT_EMAIL_RECIPIENTS),
        }

    except Exception as exc:
        logger.error(f"Failed to send audit alert email: {exc}")
        return {
            'status': 'error',
            'error': str(exc),
            'count': critical_events.count(),
        }


# =============================================================================
# CACHE TASKS
# =============================================================================

@shared_task(name='referensi.tasks.cache_warmup_task')
def cache_warmup_task(queries: List[str] = None) -> Dict[str, Any]:
    """
    Warm up cache with common search queries.

    Args:
        queries: List of queries to warm up (uses defaults if None)

    Returns:
        dict: Warmup statistics
    """
    from referensi.services.ahsp_repository import ahsp_repository

    if not queries:
        queries = [
            "pekerjaan",
            "beton",
            "tanah",
            "galian",
            "pondasi",
            "baja",
            "atap",
            "dinding",
            "pengecatan",
            "plester",
        ]

    warmed = 0
    errors = []

    for query in queries:
        try:
            # Perform search (will cache results)
            results = ahsp_repository.search_ahsp(query, limit=50)
            list(results)  # Force evaluation
            warmed += 1
        except Exception as exc:
            logger.error(f"Failed to warm up cache for query '{query}': {exc}")
            errors.append({'query': query, 'error': str(exc)})

    logger.info(f"Cache warmup completed: {warmed}/{len(queries)} queries warmed")

    return {
        'total_queries': len(queries),
        'warmed': warmed,
        'errors': errors,
    }


@shared_task(name='referensi.tasks.cleanup_stale_cache_task')
def cleanup_stale_cache_task() -> Dict[str, Any]:
    """
    Cleanup stale cache keys.

    Returns:
        dict: Cleanup statistics
    """
    from referensi.services.cache_service import CacheService

    cache = CacheService()

    # Get stats before cleanup
    stats_before = cache.get_stats()

    # For now, just get stats (actual cleanup depends on Redis configuration)
    # In production, you might want to use Redis SCAN to find and delete old keys

    logger.info("Cache cleanup task completed")

    return {
        'status': 'completed',
        'total_keys_before': stats_before.get('total_keys', 0),
        'memory_before': stats_before.get('used_memory', 'N/A'),
    }


# =============================================================================
# EXPORT TASKS (Phase 6)
# =============================================================================

@shared_task(bind=True, name='referensi.tasks.async_export_task')
def async_export_task(self, **params) -> Dict[str, Any]:
    """
    Async task for large export operations.

    Args:
        export_type: 'search' or 'multiple'
        format: 'excel' or 'pdf'
        user_id: User ID who initiated export
        ... (other parameters based on export_type)

    Returns:
        dict: Export result with file path or download URL
    """
    from referensi.services.export_service import excel_export_service
    from referensi.services.pdf_export_service import pdf_export_service
    from referensi.services.ahsp_repository import ahsp_repository
    from referensi.models import AHSPReferensi
    import os
    import uuid
    from django.conf import settings

    export_type = params.get('export_type')
    format = params.get('format')
    user_id = params.get('user_id')

    # Update task state
    self.update_state(state='PROGRESS', meta={'status': 'Preparing export...'})

    try:
        # Perform export based on type
        if export_type == 'search':
            query = params.get('query', '')
            sumber = params.get('sumber')
            klasifikasi = params.get('klasifikasi')
            limit = params.get('limit', 10000)

            # Search
            results = ahsp_repository.search_ahsp(
                query,
                sumber=sumber if sumber else None,
                klasifikasi=klasifikasi if klasifikasi else None,
                limit=limit
            )

            filters = {}
            if sumber:
                filters['sumber'] = sumber
            if klasifikasi:
                filters['klasifikasi'] = klasifikasi

            self.update_state(state='PROGRESS', meta={'status': f'Exporting {len(list(results))} results...'})

            if format == 'excel':
                output = excel_export_service.export_search_results(results, query, filters)
                filename = f"AHSP_Search_{uuid.uuid4().hex[:8]}.xlsx"
            else:
                output = pdf_export_service.export_search_results(results, query, filters)
                filename = f"AHSP_Search_{uuid.uuid4().hex[:8]}.pdf"

        elif export_type == 'multiple':
            job_ids = params.get('job_ids', [])
            include_rincian = params.get('include_rincian', False)

            jobs = AHSPReferensi.objects.filter(pk__in=job_ids)

            self.update_state(state='PROGRESS', meta={'status': f'Exporting {jobs.count()} jobs...'})

            if format == 'excel':
                output = excel_export_service.export_multiple_jobs(jobs, include_rincian=include_rincian)
                filename = f"AHSP_Export_{uuid.uuid4().hex[:8]}.xlsx"
            else:
                output = pdf_export_service.export_multiple_jobs(jobs)
                filename = f"AHSP_Export_{uuid.uuid4().hex[:8]}.pdf"

        else:
            raise ValueError(f"Invalid export_type: {export_type}")

        # Save file to media/exports
        exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
        os.makedirs(exports_dir, exist_ok=True)

        file_path = os.path.join(exports_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(output.read())

        logger.info(f"Export completed: {filename} for user {user_id}")

        # Send email notification
        if user_id:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(pk=user_id)

                download_url = f"{settings.ALLOWED_HOSTS[0]}/media/exports/{filename}"

                send_mail(
                    subject='AHSP Export Ready',
                    message=f'''
Your AHSP export is ready!

Export type: {export_type}
Format: {format.upper()}
File: {filename}

Download: {download_url}

This file will be available for 24 hours.

---
AHSP System
                    ''',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception as email_exc:
                logger.error(f"Failed to send export email: {email_exc}")

        return {
            'status': 'success',
            'filename': filename,
            'file_path': file_path,
            'download_url': f'/media/exports/{filename}',
        }

    except Exception as exc:
        logger.error(f"Export failed: {exc}")
        raise


# =============================================================================
# MONITORING TASKS
# =============================================================================

@shared_task(name='referensi.tasks.health_check_task')
def health_check_task() -> Dict[str, Any]:
    """
    Perform system health check.

    Returns:
        dict: Health check results
    """
    from referensi.services.cache_service import CacheService
    from referensi.services.ahsp_repository import ahsp_repository
    from referensi.models import AHSPReferensi, SecurityAuditLog

    health = {
        'timestamp': timezone.now().isoformat(),
        'status': 'healthy',
        'checks': {},
    }

    # Check database
    try:
        count = AHSPReferensi.objects.count()
        health['checks']['database'] = {'status': 'ok', 'ahsp_count': count}
    except Exception as exc:
        health['checks']['database'] = {'status': 'error', 'error': str(exc)}
        health['status'] = 'unhealthy'

    # Check cache
    try:
        cache = CacheService()
        stats = cache.get_stats()
        if stats.get('connected'):
            health['checks']['cache'] = {'status': 'ok', 'stats': stats}
        else:
            health['checks']['cache'] = {'status': 'error', 'error': stats.get('error')}
            health['status'] = 'degraded'
    except Exception as exc:
        health['checks']['cache'] = {'status': 'error', 'error': str(exc)}
        health['status'] = 'degraded'

    # Check search functionality
    try:
        results = ahsp_repository.search_ahsp("test", limit=1)
        health['checks']['search'] = {'status': 'ok'}
    except Exception as exc:
        health['checks']['search'] = {'status': 'error', 'error': str(exc)}
        health['status'] = 'unhealthy'

    logger.info(f"Health check completed: {health['status']}")


# =============================================================================
# PDF IMPORT TASKS
# =============================================================================

@shared_task(bind=True, name='referensi.tasks.process_ahsp_pdf_task')
def process_ahsp_pdf_task(self, file_path: str, user_id: int, file_name: str) -> Dict[str, Any]:
    """
    Async task to parse AHSP PDF.
    
    PDF Structure (from AHSP SNI 2025):
    - Column 0: No/Segment marker (A, B, C)
    - Column 1: Uraian (item name)
    - Column 2: Kode (L.01, L.02, etc)
    - Column 3: Satuan (OH, kg, m3, etc)
    - Column 4: Koefisien (0,734 - comma as decimal)
    """
    import pdfplumber
    import re
    from referensi.models_staging import AHSPImportStaging
    from django.contrib.auth import get_user_model

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"User ID {user_id} not found for PDF Import")
        return {'status': 'error', 'message': 'User not found'}

    # Only update state if running as Async Task
    if self.request.id:
        self.update_state(state='PROGRESS', meta={'status': 'Opening PDF...'})

    saved_count = 0
    current_segment = None  # A=Tenaga, B=Bahan, C=Peralatan
    table_counter = 0  # For generating pseudo AHSP code
    
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            
            # Limit pages for synchronous mode
            process_limit = 50
            
            for page_idx, page in enumerate(pdf.pages):
                if page_idx >= process_limit:
                    logger.warning(f"Stopping PDF import at page {process_limit}")
                    break

                if self.request.id:
                    self.update_state(state='PROGRESS', meta={
                        'status': f'Processing page {page_idx+1}/{total_pages} ({saved_count} items)'
                    })
                
                tables = page.extract_tables()
                
                for table in tables:
                    table_counter += 1
                    parent_ahsp_code = f"PDF.{page_idx+1}.{table_counter}"  # Pseudo code
                    
                    # Save table as HEADING
                    AHSPImportStaging.objects.create(
                        user=user,
                        file_name=file_name,
                        kode_item=parent_ahsp_code,
                        uraian_item=f"Tabel Halaman {page_idx+1} #{table_counter}",
                        segment_type='HEADING',
                        is_valid=True
                    )
                    
                    for row in table:
                        if not row or len(row) < 5:
                            continue
                        
                        # Clean cells
                        cells = [str(c).strip() if c else "" for c in row]
                        col0 = cells[0]  # No / Segment marker
                        col1 = cells[1]  # Uraian
                        col2 = cells[2] if len(cells) > 2 else ""  # Kode
                        col3 = cells[3] if len(cells) > 3 else ""  # Satuan
                        col4 = cells[4] if len(cells) > 4 else ""  # Koefisien
                        
                        # Skip header row
                        if col0.upper() in ['NO', 'NO.'] or 'URAIAN' in col1.upper():
                            continue
                        
                        # Skip subtotal rows
                        if 'JUMLAH' in col0.upper() or 'JUMLAH' in col1.upper():
                            continue
                        
                        # Detect segment marker (A, B, C)
                        if col0.upper() in ['A', 'B', 'C']:
                            current_segment = col0.upper()
                            continue
                        
                        # Skip D, E, F segments (calculated totals)
                        if col0.upper() in ['D', 'E', 'F']:
                            current_segment = 'IGNORE'
                            continue
                        
                        if current_segment == 'IGNORE':
                            continue
                        
                        # Extract item data
                        uraian = col1.replace('\n', ' ').strip()
                        kode = col2.strip()
                        satuan = col3.strip()
                        
                        # Parse koefisien (handle comma as decimal)
                        koef_str = col4.replace(',', '.').strip()
                        try:
                            koefisien = float(koef_str)
                        except (ValueError, TypeError):
                            koefisien = 0.0
                        
                        # Only save if we have meaningful data
                        if uraian and (kode or koefisien > 0):
                            AHSPImportStaging.objects.create(
                                user=user,
                                file_name=file_name,
                                parent_ahsp_code=parent_ahsp_code,
                                segment_type=current_segment or 'A',
                                kode_item=kode or f"ITEM.{saved_count+1}",
                                uraian_item=uraian,
                                satuan_item=satuan,
                                koefisien=koefisien
                            )
                            saved_count += 1
    
    except Exception as e:
        logger.error(f"PDF Import Error: {e}")
        return {'status': 'error', 'message': str(e)}

    return {'status': 'success', 'count': saved_count}

