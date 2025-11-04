"""
Audit Dashboard Views - Phase 2

Provides web interface for viewing and managing security audit logs.

Features:
- View all audit logs with filtering
- Dashboard with statistics
- Export audit logs
- Mark events as resolved
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from referensi.models import SecurityAuditLog, AuditLogSummary


@login_required
@permission_required('referensi.view_ahsp_stats', raise_exception=True)
def audit_dashboard(request):
    """
    Main audit dashboard with statistics and recent events.

    Displays:
    - Summary cards (total events, critical events, unresolved, etc.)
    - Recent events timeline
    - Charts and graphs
    - Quick filters
    """
    # Date range for dashboard (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)

    # Get statistics
    total_events = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date
    ).count()

    critical_events = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date,
        severity=SecurityAuditLog.SEVERITY_CRITICAL
    ).count()

    unresolved_events = SecurityAuditLog.objects.filter(
        resolved=False
    ).count()

    # Events by severity (last 30 days)
    events_by_severity = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('severity').annotate(
        count=Count('id')
    ).order_by('severity')

    # Events by category (last 30 days)
    events_by_category = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Recent critical events
    recent_critical = SecurityAuditLog.objects.filter(
        severity=SecurityAuditLog.SEVERITY_CRITICAL
    ).order_by('-timestamp')[:10]

    # Recent events (last 20)
    recent_events = SecurityAuditLog.objects.all().order_by('-timestamp')[:20]

    # Events timeline (last 7 days, grouped by day)
    timeline_data = []
    for i in range(7):
        day_start = end_date - timedelta(days=i)
        day_end = day_start + timedelta(days=1)

        day_count = SecurityAuditLog.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end
        ).count()

        timeline_data.append({
            'date': day_start.strftime('%Y-%m-%d'),
            'count': day_count
        })

    timeline_data.reverse()

    context = {
        'total_events': total_events,
        'critical_events': critical_events,
        'unresolved_events': unresolved_events,
        'events_by_severity': events_by_severity,
        'events_by_category': events_by_category,
        'recent_critical': recent_critical,
        'recent_events': recent_events,
        'timeline_data': timeline_data,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'referensi/audit/dashboard.html', context)


@login_required
@permission_required('referensi.view_ahsp_stats', raise_exception=True)
def audit_logs_list(request):
    """
    List all audit logs with filtering and pagination.

    Filters:
    - severity: Filter by severity level
    - category: Filter by event category
    - resolved: Filter by resolution status
    - date_from: Start date
    - date_to: End date
    - search: Search in message and event_type
    """
    # Get filter parameters
    severity = request.GET.get('severity', '')
    category = request.GET.get('category', '')
    resolved = request.GET.get('resolved', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')

    # Build queryset
    logs = SecurityAuditLog.objects.all()

    if severity:
        logs = logs.filter(severity=severity)

    if category:
        logs = logs.filter(category=category)

    if resolved == 'true':
        logs = logs.filter(resolved=True)
    elif resolved == 'false':
        logs = logs.filter(resolved=False)

    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            # Add one day to include the entire end date
            to_date = to_date + timedelta(days=1)
            logs = logs.filter(timestamp__lt=to_date)
        except ValueError:
            pass

    if search:
        logs = logs.filter(
            Q(message__icontains=search) |
            Q(event_type__icontains=search) |
            Q(username__icontains=search)
        )

    # Order by most recent first
    logs = logs.order_by('-timestamp')

    # Pagination
    page_number = request.GET.get('page', 1)
    paginator = Paginator(logs, 50)  # 50 logs per page
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'severity_choices': SecurityAuditLog.SEVERITY_CHOICES,
        'category_choices': SecurityAuditLog.CATEGORY_CHOICES,
        'filters': {
            'severity': severity,
            'category': category,
            'resolved': resolved,
            'date_from': date_from,
            'date_to': date_to,
            'search': search,
        }
    }

    return render(request, 'referensi/audit/logs_list.html', context)


@login_required
@permission_required('referensi.view_ahsp_stats', raise_exception=True)
def audit_log_detail(request, log_id):
    """
    View detailed information about a specific audit log entry.
    """
    log = get_object_or_404(SecurityAuditLog, id=log_id)

    context = {
        'log': log,
    }

    return render(request, 'referensi/audit/log_detail.html', context)


@login_required
@permission_required('referensi.import_ahsp_data', raise_exception=True)
@require_http_methods(["POST"])
def mark_log_resolved(request, log_id):
    """
    Mark an audit log as resolved.

    POST parameters:
    - notes: Optional resolution notes
    """
    log = get_object_or_404(SecurityAuditLog, id=log_id)

    notes = request.POST.get('notes', '')
    log.mark_resolved(user=request.user, notes=notes)

    # Return JSON for AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'message': 'Log marked as resolved'
        })

    # Redirect for normal requests
    return redirect('referensi:audit_log_detail', log_id=log_id)


@login_required
@permission_required('referensi.view_ahsp_stats', raise_exception=True)
def audit_statistics(request):
    """
    Detailed statistics page with charts and reports.

    Shows:
    - Trends over time
    - Top users by events
    - Top IP addresses
    - Event type distribution
    - Response time analysis
    """
    # Date range (last 90 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=90)

    # Events by day (for trend chart)
    daily_events = []
    for i in range(90):
        day = end_date - timedelta(days=89-i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count = SecurityAuditLog.objects.filter(
            timestamp__gte=day_start,
            timestamp__lt=day_end
        ).count()

        daily_events.append({
            'date': day.strftime('%Y-%m-%d'),
            'count': count
        })

    # Top users by events
    top_users = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date,
        user__isnull=False
    ).values('username').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Top IP addresses
    top_ips = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date,
        ip_address__isnull=False
    ).values('ip_address').annotate(
        count=Count('id')
    ).order_by('-count')[:10]

    # Event type distribution
    event_types = SecurityAuditLog.objects.filter(
        timestamp__gte=start_date
    ).values('event_type').annotate(
        count=Count('id')
    ).order_by('-count')[:15]

    # Events by severity and category (matrix)
    severity_category_matrix = []
    for severity_code, severity_label in SecurityAuditLog.SEVERITY_CHOICES:
        row = {'severity': severity_label, 'categories': []}
        for category_code, category_label in SecurityAuditLog.CATEGORY_CHOICES:
            count = SecurityAuditLog.objects.filter(
                timestamp__gte=start_date,
                severity=severity_code,
                category=category_code
            ).count()
            row['categories'].append({
                'category': category_label,
                'count': count
            })
        severity_category_matrix.append(row)

    context = {
        'daily_events': daily_events,
        'top_users': top_users,
        'top_ips': top_ips,
        'event_types': event_types,
        'severity_category_matrix': severity_category_matrix,
        'start_date': start_date,
        'end_date': end_date,
    }

    return render(request, 'referensi/audit/statistics.html', context)


@login_required
@permission_required('referensi.view_ahsp_stats', raise_exception=True)
def export_audit_logs(request):
    """
    Export audit logs to CSV.

    Applies same filters as logs_list view.
    """
    import csv

    # Get filter parameters (same as logs_list)
    severity = request.GET.get('severity', '')
    category = request.GET.get('category', '')
    resolved = request.GET.get('resolved', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    search = request.GET.get('search', '')

    # Build queryset (same logic as logs_list)
    logs = SecurityAuditLog.objects.all()

    if severity:
        logs = logs.filter(severity=severity)
    if category:
        logs = logs.filter(category=category)
    if resolved == 'true':
        logs = logs.filter(resolved=True)
    elif resolved == 'false':
        logs = logs.filter(resolved=False)
    if date_from:
        try:
            from_date = timezone.datetime.strptime(date_from, '%Y-%m-%d')
            logs = logs.filter(timestamp__gte=from_date)
        except ValueError:
            pass
    if date_to:
        try:
            to_date = timezone.datetime.strptime(date_to, '%Y-%m-%d')
            to_date = to_date + timedelta(days=1)
            logs = logs.filter(timestamp__lt=to_date)
        except ValueError:
            pass
    if search:
        logs = logs.filter(
            Q(message__icontains=search) |
            Q(event_type__icontains=search) |
            Q(username__icontains=search)
        )

    logs = logs.order_by('-timestamp')

    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'Severity', 'Category', 'Event Type',
        'Username', 'IP Address', 'Message', 'Resolved'
    ])

    for log in logs[:10000]:  # Limit to 10,000 rows
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.get_severity_display(),
            log.get_category_display(),
            log.event_type,
            log.username or 'Anonymous',
            log.ip_address or 'N/A',
            log.message,
            'Yes' if log.resolved else 'No'
        ])

    return response
