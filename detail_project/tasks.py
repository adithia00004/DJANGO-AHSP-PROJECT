"""
Celery tasks for AHSP Project - Async Export Operations

This module contains background tasks for heavy export operations.
All PDF and Word exports are processed asynchronously to prevent browser timeouts.

Usage:
    from detail_project.tasks import generate_export_async
    
    task = generate_export_async.delay(
        project_id=160,
        export_type='rekap-rab',
        format_type='pdf',
        user_id=1
    )
    
    # Check status
    result = AsyncResult(task.id)
    print(result.state)  # PENDING, PROCESSING, SUCCESS, FAILURE
"""

import os
import logging
from celery import shared_task
from django.contrib.auth import get_user_model
from django.conf import settings

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=3, time_limit=600)
def generate_export_async(self, project_id, export_type, format_type, user_id, options=None):
    """
    Unified async export task for all PDF/Word exports.
    
    This task handles background generation of heavy exports to prevent browser timeouts.
    User can close browser and return later to download the completed export.
    
    Args:
        project_id (int): Project ID to export
        export_type (str): Type of export
            - 'rekap-rab': Rekap RAB summary
            - 'jadwal-pekerjaan': Gantt chart & schedule
            - 'harga-items': Price items listing
            - 'rincian-ahsp': Detailed AHSP breakdown
            - 'rekap-kebutuhan': Material requirements
            - 'volume-pekerjaan': Work volume
        format_type (str): Output format ('pdf' or 'word')
        user_id (int): User requesting export
        options (dict, optional): Export configuration options
    
    Returns:
        dict: {
            'status': 'SUCCESS',
            'file_path': '/path/to/export.pdf',
            'file_size': 1024000,
            'export_type': 'rekap-rab',
            'format': 'pdf'
        }
    
    Raises:
        ValueError: If export_type or format_type is invalid
        Exception: If export generation fails
    
    Example:
        >>> task = generate_export_async.delay(160, 'rekap-rab', 'pdf', 1)
        >>> task.id
        'abc-123-def'
        >>> result = task.get(timeout=60)
        >>> print(result['file_path'])
    """
    from detail_project.models import Project
    
    try:
        # Update task state to PROCESSING
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Loading project data...',
                'progress': 0,
                'total': 100
            }
        )
        
        # Validate and load project
        try:
            project = Project.objects.select_related('owner').get(id=project_id)
        except Project.DoesNotExist:
            raise ValueError(f"Project {project_id} not found")
        
        # Validate user
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            raise ValueError(f"User {user_id} not found")
        
        # Validate export type
        valid_types = [
            'rekap-rab', 'jadwal-pekerjaan', 'harga-items',
            'rincian-ahsp', 'rekap-kebutuhan', 'volume-pekerjaan'
        ]
        if export_type not in valid_types:
            raise ValueError(f"Invalid export_type: {export_type}. Must be one of {valid_types}")
        
        # Validate format
        if format_type not in ['pdf', 'word']:
            raise ValueError(f"Invalid format_type: {format_type}. Must be 'pdf' or 'word'")
        
        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={
                'status': f'Generating {export_type} {format_type.upper()}...',
                'progress': 20,
                'total': 100
            }
        )
        
        # Dynamic routing to appropriate exporter
        # Convert export_type to method name: 'rekap-rab' -> 'export_rekap_rab'
        export_type_normalized = export_type.replace('-', '_')
        method_name = f"export_{export_type_normalized}"
        
        # Use ExportManager which handles config creation properly
        from detail_project.exports.export_manager import ExportManager
        
        manager = ExportManager(project, user)
        
        # Check if export method exists on manager
        if not hasattr(manager, method_name):
            raise ValueError(
                f"Export method '{method_name}' not found in ExportManager"
            )
        
        # Progress callback for tracking
        def progress_callback(current, total, message):
            """Update task progress during export generation."""
            progress_pct = int((current / total) * 80) + 20  # 20-100% range
            self.update_state(
                state='PROCESSING',
                meta={
                    'status': message,
                    'progress': progress_pct,
                    'total': 100
                }
            )
        
        # Execute export
        logger.info(
            f"Starting export: project={project_id}, type={export_type}, "
            f"format={format_type}, user={user_id}"
        )
        
        export_method = getattr(manager, method_name)
        
        # Call export method with format_type
        # ExportManager methods take format_type as first arg
        response = export_method(format_type)
        
        # ExportManager returns HttpResponse, we need to save content to file
        import tempfile
        import time
        
        # Determine file extension
        ext = 'pdf' if format_type == 'pdf' else 'docx'
        
        # Create exports directory if not exists
        exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports', 'async')
        os.makedirs(exports_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = int(time.time())
        filename = f"{export_type_normalized}_{project_id}_{timestamp}.{ext}"
        file_path = os.path.join(exports_dir, filename)
        
        # Write response content to file
        with open(file_path, 'wb') as f:
            f.write(response.content)
        
        file_size = os.path.getsize(file_path)
        
        logger.info(
            f"Export completed: {file_path} ({file_size} bytes)"
        )
        
        # Return success result
        return {
            'status': 'SUCCESS',
            'file_path': file_path,
            'file_size': file_size,
            'export_type': export_type,
            'format': format_type,
            'project_id': project_id
        }
    
    except Exception as exc:
        logger.error(
            f"Export failed: project={project_id}, type={export_type}, "
            f"format={format_type}, error={str(exc)}",
            exc_info=True
        )
        
        # Update state to FAILURE with error details
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(exc),
                'export_type': export_type,
                'format': format_type
            }
        )
        
        # Re-raise for Celery to handle retry logic
        raise


@shared_task
def cleanup_old_exports():
    """
    Cleanup old export files (older than 24 hours).
    
    This task should be run periodically via Celery Beat to prevent
    disk space issues from accumulated export files.
    
    Returns:
        dict: {
            'deleted_count': 10,
            'freed_bytes': 5242880
        }
    """
    import time
    from pathlib import Path
    
    exports_dir = os.path.join(settings.MEDIA_ROOT, 'exports')
    if not os.path.exists(exports_dir):
        return {'deleted_count': 0, 'freed_bytes': 0}
    
    deleted_count = 0
    freed_bytes = 0
    cutoff_time = time.time() - (24 * 60 * 60)  # 24 hours ago
    
    for export_file in Path(exports_dir).rglob('*'):
        if export_file.is_file():
            if export_file.stat().st_mtime < cutoff_time:
                file_size = export_file.stat().st_size
                try:
                    export_file.unlink()
                    deleted_count += 1
                    freed_bytes += file_size
                    logger.info(f"Deleted old export: {export_file}")
                except Exception as e:
                    logger.error(f"Failed to delete {export_file}: {e}")
    
    logger.info(
        f"Export cleanup: deleted {deleted_count} files, "
        f"freed {freed_bytes / 1024 / 1024:.2f} MB"
    )
    
    return {
        'deleted_count': deleted_count,
        'freed_bytes': freed_bytes
    }
