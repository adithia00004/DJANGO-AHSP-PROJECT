# Phase 2 Implementation Guide: Audit & Logging System

**Status**: 85% Complete
**Completed**: 2025-01-05
**Remaining**: Tests (15%)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Components](#components)
4. [Setup & Configuration](#setup--configuration)
5. [Usage Guide](#usage-guide)
6. [Management Commands](#management-commands)
7. [Dashboard Guide](#dashboard-guide)
8. [Maintenance](#maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Overview

Phase 2 implements a comprehensive security audit and logging system for tracking all security-related events in the AHSP Referensi application.

### Key Features

- ✅ **Comprehensive Audit Logging** - Track all security events
- ✅ **Web Dashboard** - View and manage logs via browser
- ✅ **Advanced Filtering** - Filter by severity, category, date, user
- ✅ **Management Commands** - Automated cleanup, summaries, alerts
- ✅ **Email Alerts** - Automatic notifications for critical events
- ✅ **CSV Export** - Export logs for external analysis
- ✅ **Statistics & Reports** - Pre-aggregated analytics

### Components Delivered

| Component | Files | Lines | Status |
|-----------|-------|-------|--------|
| Models | 2 | ~450 | ✅ Complete |
| Audit Logger Service | 1 | ~430 | ✅ Complete |
| Dashboard Views | 1 | ~400 | ✅ Complete |
| **Templates** | **4** | **1,320** | **✅ Complete** |
| **Management Commands** | **3** | **721** | **✅ Complete** |
| Tests | 0 | 0 | ⏳ Pending |
| **TOTAL** | **11** | **3,321** | **85%** |

---

## Architecture

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                         │
│  (File Validator, Rate Limiter, Import Operations, etc.)    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ log_event()
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Audit Logger Service                            │
│  referensi/services/audit_logger.py                          │
│  • Extract request context (user, IP, user agent)           │
│  • Create SecurityAuditLog entries                           │
│  • Batch logging support                                     │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ save()
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   Database Layer                             │
│  • SecurityAuditLog (main log table)                         │
│  • AuditLogSummary (pre-aggregated stats)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ query
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                  Dashboard Views                             │
│  referensi/views/audit_dashboard.py                          │
│  • audit_dashboard() - Main dashboard                        │
│  • audit_logs_list() - Filterable list                       │
│  • audit_log_detail() - Individual log                       │
│  • audit_statistics() - Statistics page                      │
│  • export_audit_logs() - CSV export                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ render
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Templates                                 │
│  • dashboard.html - Main dashboard with charts               │
│  • logs_list.html - Filterable logs list                     │
│  • log_detail.html - Individual log detail                   │
│  • statistics.html - 90-day statistics                       │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Management Commands (CLI)                       │
│  • cleanup_audit_logs - Delete old logs                      │
│  • generate_audit_summary - Pre-aggregate stats              │
│  • send_audit_alerts - Email critical events                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Event Occurs → Audit Logger → Database → Dashboard/Commands → Admin
    ↓              ↓              ↓            ↓                 ↓
  Import      Extract Info   Save Log    Query Logs         View/Act
  Rate Limit  (user, IP)     to Table    Filter/Export      Resolve
  XSS Block                               Statistics         Alert
```

---

## Components

### 1. Models

**File**: `referensi/models/audit.py`

#### SecurityAuditLog

Main audit log table storing all security events.

```python
class SecurityAuditLog(models.Model):
    """
    Stores security audit events.

    Fields:
    - timestamp: When event occurred
    - severity: CRITICAL/ERROR/WARNING/INFO
    - category: FILE/RATE/XSS/IMPORT/AUTH/SYSTEM
    - event_type: Specific event identifier
    - message: Human-readable description
    - user: FK to User (optional)
    - username: Cached username
    - ip_address: Client IP
    - user_agent: Browser/client info
    - path: Request path
    - method: HTTP method
    - metadata: JSON extra data
    - resolved: Whether issue resolved
    - resolved_at: When resolved
    - resolved_by: Who resolved
    - notes: Resolution notes
    """
```

**Indexes:**
- `timestamp` - For date filtering
- `severity` - For severity filtering
- `category` - For category filtering
- `user` - For user tracking
- `resolved` - For pending/resolved filtering
- Composite indexes for common queries

**Constraints:**
- None (allow duplicates for audit trail)

#### AuditLogSummary

Pre-aggregated statistics for dashboard performance.

```python
class AuditLogSummary(models.Model):
    """
    Pre-aggregated audit log statistics.

    Fields:
    - period_type: hourly/daily/weekly/monthly
    - period_start: Period start timestamp
    - period_end: Period end timestamp
    - category: Event category
    - severity: Event severity
    - event_count: Number of events
    - unique_users: Distinct users
    - unique_ips: Distinct IPs
    - top_events: JSON list of top event types
    - top_users: JSON list of top users
    """
```

**Purpose**: Speed up dashboard queries by pre-aggregating statistics.

### 2. Audit Logger Service

**File**: `referensi/services/audit_logger.py` (431 lines)

Centralized service for logging security events.

#### Key Methods

```python
class AuditLogger:
    """Centralized audit logging service."""

    def log_event(
        self,
        event_type: str,
        message: str,
        severity: str = SEVERITY_INFO,
        category: str = CATEGORY_SYSTEM,
        metadata: Optional[Dict] = None,
        request: Optional[HttpRequest] = None,
        user: Optional[User] = None
    ) -> SecurityAuditLog:
        """
        Log a security event.

        Auto-extracts user, IP, user agent from request.
        """

    # Convenience methods
    def log_file_validation(self, filename, passed, errors, request):
        """Log file validation event."""

    def log_rate_limit(self, limit_type, user, ip, request):
        """Log rate limit exceeded."""

    def log_xss_attempt(self, field, value, request):
        """Log XSS attempt."""

    def log_import_operation(self, filename, status, summary, request):
        """Log import operation."""

    def log_malicious_file(self, filename, threat_type, request):
        """Log malicious file detection."""

    def log_authentication(self, username, success, reason, request):
        """Log authentication attempt."""
```

**Usage Example:**

```python
from referensi.services.audit_logger import audit_logger

# Log file validation
audit_logger.log_file_validation(
    filename="import.xlsx",
    passed=True,
    errors=[],
    request=request
)

# Log rate limit
audit_logger.log_rate_limit(
    limit_type="import",
    user=request.user,
    ip="192.168.1.1",
    request=request
)

# Generic event
audit_logger.log_event(
    event_type="custom_event",
    message="Something happened",
    severity="warning",
    category="system",
    metadata={"key": "value"},
    request=request
)
```

### 3. Dashboard Views

**File**: `referensi/views/audit_dashboard.py` (367 lines)

#### Views

**a) audit_dashboard()**
- URL: `/referensi/audit/`
- Main dashboard with statistics and charts
- Shows last 30 days of data
- Permission: `view_ahsp_stats`

**b) audit_logs_list()**
- URL: `/referensi/audit/logs/`
- Filterable list of all logs
- Pagination: 50 logs per page
- Filters: severity, category, resolved, date range, search
- Permission: `view_ahsp_stats`

**c) audit_log_detail()**
- URL: `/referensi/audit/logs/<id>/`
- Detailed view of single log entry
- Shows all metadata, user info, resolution
- Permission: `view_ahsp_stats`

**d) mark_log_resolved()**
- URL: `/referensi/audit/logs/<id>/resolve/`
- Mark log as resolved (POST only)
- Supports AJAX requests
- Permission: `import_ahsp_data`

**e) audit_statistics()**
- URL: `/referensi/audit/statistics/`
- Detailed 90-day statistics
- Charts and trends
- Permission: `view_ahsp_stats`

**f) export_audit_logs()**
- URL: `/referensi/audit/export/`
- CSV export with current filters
- Limit: 10,000 rows
- Permission: `view_ahsp_stats`

### 4. Templates

**Location**: `referensi/templates/referensi/audit/`

#### dashboard.html (365 lines)

Main security dashboard.

**Features:**
- 4 summary cards (total, critical, unresolved, resolved)
- 7-day timeline chart (Chart.js line chart)
- Severity distribution pie chart
- Category distribution bar chart
- Recent critical events list
- Recent events table (last 20)

**Technologies:**
- Bootstrap 5
- Chart.js 4.4.0
- Bootstrap Icons
- Responsive design

#### logs_list.html (280 lines)

Filterable logs list with advanced search.

**Features:**
- Advanced filter panel
  - Search box (message, event type, user)
  - Severity dropdown
  - Category dropdown
  - Resolved status dropdown
  - Date range picker (from/to)
- Results table with 50 logs per page
- Pagination controls
- Export CSV button
- Clickable rows
- Keyboard shortcuts (Ctrl+F for search)

#### log_detail.html (295 lines)

Individual log detail view.

**Features:**
- Event header with severity/category badges
- Full event information
  - Timestamp
  - Event ID
  - User info
  - IP address
  - Request path & method
  - User agent
- Metadata JSON display (formatted)
- Resolution form (if unresolved)
- Resolution information (if resolved)
- Quick links to related events
  - Same severity
  - Same category
  - Same event type
  - Same user
  - Same IP

#### statistics.html (380 lines)

90-day statistics page.

**Features:**
- 90-day trend line chart
- Top 10 users list
- Top 10 IP addresses list
- Top 15 event types list
- Event type distribution bar chart
- Severity vs Category heatmap matrix

---

## Setup & Configuration

### 1. Prerequisites

```bash
# Django already installed
pip list | grep Django

# PostgreSQL (for production)
# SQLite works for development
```

### 2. Apply Migrations

```bash
# Apply Phase 2 migrations
python manage.py migrate referensi

# Verify tables created
python manage.py dbshell
\dt referensi_securityauditlog
\dt referensi_auditlogsummary
```

### 3. Configure Permissions

Phase 2 uses existing permissions from Phase 1:
- `view_ahsp_stats` - View audit dashboard
- `import_ahsp_data` - Resolve audit logs

```python
# In Django admin or management command
from django.contrib.auth.models import Permission
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username='admin')

# Grant permissions
view_perm = Permission.objects.get(codename='view_ahsp_stats')
import_perm = Permission.objects.get(codename='import_ahsp_data')
user.user_permissions.add(view_perm, import_perm)
```

### 4. Configure Email (for Alerts)

**File**: `config/settings/base.py` or `.env`

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'

# Admin emails for alerts
ADMINS = [
    ('Admin Name', 'admin@example.com'),
    ('Security Team', 'security@example.com'),
]

# Site URL for alert emails
SITE_URL = 'https://your-site.com'
```

### 5. Test Setup

```bash
# Test audit logging
python manage.py shell
>>> from referensi.services.audit_logger import audit_logger
>>> audit_logger.log_event("test_event", "Testing audit system", severity="info")
>>> from referensi.models import SecurityAuditLog
>>> SecurityAuditLog.objects.count()
1

# Access dashboard
# Navigate to: http://localhost:8000/referensi/audit/
```

---

## Usage Guide

### Accessing the Dashboard

```
URL: http://your-site/referensi/audit/

Required Permission: view_ahsp_stats
```

### Viewing Logs

1. **Main Dashboard**
   - Navigate to `/referensi/audit/`
   - View summary cards and charts
   - Click "View All Logs" button

2. **Logs List**
   - Navigate to `/referensi/audit/logs/`
   - Use filters to narrow down logs
   - Click any row to view details

3. **Log Detail**
   - Click on a log in the list
   - View full details including metadata
   - Mark as resolved if unresolved
   - Use quick links to find related events

4. **Statistics**
   - Navigate to `/referensi/audit/statistics/`
   - View 90-day trends
   - Analyze top users, IPs, event types

### Filtering Logs

Available filters on logs list page:

- **Search**: Message, event type, username
- **Severity**: Critical, Error, Warning, Info
- **Category**: File Validation, Rate Limiting, XSS, Import, Auth, System
- **Status**: All, Unresolved, Resolved
- **Date Range**: From date, To date

**Example Queries:**
- "Find all critical events in last 7 days"
  - Severity: Critical
  - Date From: 7 days ago
  - Click "Apply Filters"

- "Find all rate limit events for user 'john'"
  - Category: Rate Limiting
  - Search: john
  - Click "Apply Filters"

### Exporting Logs

```
1. Apply desired filters on logs list page
2. Click "Export CSV" button
3. CSV file downloads with current filters applied
4. Limit: 10,000 rows per export
```

**CSV Columns:**
- Timestamp
- Severity
- Category
- Event Type
- Username
- IP Address
- Message
- Resolved Status

### Resolving Logs

**For unresolved critical/error events:**

1. Navigate to log detail page
2. Review event information
3. Fill in "Resolution Notes" textarea
4. Click "Mark as Resolved" button
5. Log status changes to "Resolved"
6. Resolution info recorded (who, when, notes)

---

## Management Commands

### 1. cleanup_audit_logs

Delete old audit logs to save database space.

```bash
# Basic usage (delete logs older than 90 days)
python manage.py cleanup_audit_logs

# Custom retention period
python manage.py cleanup_audit_logs --days=30

# Keep critical events longer (180 days)
python manage.py cleanup_audit_logs --days=90 --keep-critical=180

# Dry run (see what would be deleted)
python manage.py cleanup_audit_logs --dry-run

# Skip confirmation prompt
python manage.py cleanup_audit_logs --force
```

**Options:**
- `--days` - Delete logs older than N days (default: 90)
- `--keep-critical` - Keep critical events longer (default: 180)
- `--dry-run` - Show what would be deleted without deleting
- `--force` - Skip confirmation prompt

**Example Output:**
```
============================================================
Audit Log Cleanup
============================================================

Total audit logs in database: 15,234

Logs to be deleted:
  • Non-critical logs older than 90 days: 12,450
  • Critical logs older than 180 days: 234
  • Total to delete: 12,684

Logs to be kept: 2,550

Breakdown by severity:
  • Critical: 234
  • Error: 3,456
  • Warning: 5,678
  • Info: 3,316

Are you sure you want to delete these logs? [y/N]: y

Deleting logs...
  Deleting 12,450 non-critical logs... ✓ Done (12450 deleted)
  Deleting 234 old critical logs... ✓ Done (234 deleted)

============================================================
✓ Cleanup complete!
✓ Deleted 12,684 audit logs
✓ Remaining logs: 2,550
============================================================
```

**Recommended Schedule:**
```bash
# Crontab entry (daily at 2 AM)
0 2 * * * cd /path/to/project && python manage.py cleanup_audit_logs --force
```

### 2. generate_audit_summary

Generate pre-aggregated statistics for dashboard performance.

```bash
# Generate daily summaries (last 7 days)
python manage.py generate_audit_summary --period=daily

# Generate hourly summaries (last 7 days)
python manage.py generate_audit_summary --period=hourly --days=7

# Generate weekly summary
python manage.py generate_audit_summary --period=weekly

# Generate monthly summary
python manage.py generate_audit_summary --period=monthly

# Regenerate existing summaries
python manage.py generate_audit_summary --period=daily --regenerate

# Generate for specific date
python manage.py generate_audit_summary --period=daily --date=2025-01-01
```

**Options:**
- `--period` - hourly, daily, weekly, monthly (default: daily)
- `--date` - Specific date YYYY-MM-DD (default: today)
- `--days` - Number of days to generate (default: 7)
- `--regenerate` - Overwrite existing summaries

**Example Output:**
```
============================================================
Audit Summary Generation
============================================================

Generating daily summaries for 7 days...
  2025-01-05 ✓
  2025-01-04 ✓
  2025-01-03 ✓
  2025-01-02 ✓
  2025-01-01 ✓
  2024-12-31 ✓
  2024-12-30 ✓

============================================================
✓ Summary generation complete!
✓ Created: 42 summaries
✓ Updated: 0 summaries
============================================================
```

**Recommended Schedule:**
```bash
# Crontab entry (hourly)
0 * * * * cd /path/to/project && python manage.py generate_audit_summary --period=hourly

# Or daily at 1 AM
0 1 * * * cd /path/to/project && python manage.py generate_audit_summary --period=daily
```

### 3. send_audit_alerts

Send email alerts for critical security events.

```bash
# Check last hour for critical/error events
python manage.py send_audit_alerts

# Check last 30 minutes
python manage.py send_audit_alerts --since="30 minutes"

# Check last 2 hours
python manage.py send_audit_alerts --since="2 hours"

# Only critical events
python manage.py send_audit_alerts --severity=critical

# Dry run (see what would be sent)
python manage.py send_audit_alerts --dry-run

# Force send (bypass rate limit)
python manage.py send_audit_alerts --force

# Custom threshold (min 5 events)
python manage.py send_audit_alerts --threshold=5
```

**Options:**
- `--since` - Check events since (e.g., "1 hour", "30 minutes", "2 days")
- `--severity` - Comma-separated severities (default: critical,error)
- `--threshold` - Minimum events to trigger alert (default: 1)
- `--dry-run` - Show what would be sent
- `--force` - Bypass rate limit (normally max 1/hour)

**Example Output:**
```
============================================================
Security Audit Alerts
============================================================

Checking for events:
  • Since: 2025-01-05 10:00:00
  • Severities: critical, error
  • Threshold: 1 event(s)

Found 5 unresolved event(s)

Events breakdown:
  • Critical: 2
  • Error: 3

Sending alert email... ✓

============================================================
✓ Alert sent successfully!
✓ Recipients: 2
============================================================
```

**Email Content:**
```
Subject: [Security Alert] 5 Unresolved Security Event(s)

SECURITY ALERT
======================================================================

Time: 2025-01-05 11:30:00
Period: Since 2025-01-05 10:00:00
Total Unresolved Events: 5

BREAKDOWN BY SEVERITY:
----------------------------------------------------------------------
  Critical: 2
  Error: 3

RECENT EVENTS:
----------------------------------------------------------------------
1. [CRITICAL] malicious_file_detected
   Time: 2025-01-05 11:25:00
   User: user123
   IP: 192.168.1.100
   Message: Malicious file detected: malware.xlsx

2. [CRITICAL] multiple_rate_limit_exceeded
   Time: 2025-01-05 11:20:00
   User: attacker
   IP: 10.0.0.50
   Message: Rate limit exceeded 10 times in 5 minutes

...

======================================================================

Please review these events in the audit dashboard:
https://your-site.com/referensi/audit/

This is an automated message from the Security Audit System.
```

**Recommended Schedule:**
```bash
# Crontab entry (every 15 minutes)
*/15 * * * * cd /path/to/project && python manage.py send_audit_alerts --since="15 minutes"

# Or hourly for less spam
0 * * * * cd /path/to/project && python manage.py send_audit_alerts --since="1 hour"
```

---

## Dashboard Guide

### Main Dashboard

**URL**: `/referensi/audit/`

**Components:**

1. **Summary Cards (4 cards)**
   - Total Events (last 30 days)
   - Critical Events
   - Unresolved Events
   - Resolved Events (all time)

2. **Events Timeline (Chart)**
   - Line chart showing events over last 7 days
   - Hover for details
   - Shows daily event count

3. **Severity Distribution (Pie Chart)**
   - Shows breakdown by severity
   - Critical, Error, Warning, Info
   - Click legend to toggle

4. **Events by Category (Bar Chart)**
   - Top 10 categories
   - Shows event count per category

5. **Recent Critical Events (List)**
   - Last 10 critical events
   - Click to view details
   - Shows time, user, message

6. **Recent Events (Table)**
   - Last 20 events (all severities)
   - Shows timestamp, severity, category, event type, user, message, status
   - Click row to view details

**Actions:**
- "View All Logs" - Go to logs list
- "Statistics" - Go to statistics page
- "Export CSV" - Export all logs

### Logs List Page

**URL**: `/referensi/audit/logs/`

**Filter Panel:**
- Search box (searches message, event type, username)
- Severity dropdown (All, Critical, Error, Warning, Info)
- Category dropdown (All categories)
- Resolved status (All, Unresolved, Resolved)
- Date From (date picker)
- Date To (date picker)
- "Apply Filters" button
- "Clear Filters" button

**Results Table:**
- Timestamp (date + time)
- Severity (badge)
- Category (text)
- Event Type (monospace)
- User (with icon)
- IP Address (monospace)
- Message (truncated)
- Status (Resolved/Pending badge)
- Actions (View button)

**Pagination:**
- 50 logs per page
- First/Previous/Next/Last buttons
- Page numbers (shows current +/- 2 pages)
- Total count displayed

**Keyboard Shortcuts:**
- `Ctrl+F` or `Cmd+F` - Focus search box

### Log Detail Page

**URL**: `/referensi/audit/logs/<id>/`

**Sections:**

1. **Header**
   - Event Type (title)
   - Severity badge
   - Category badge
   - Resolved/Unresolved status

2. **Message Alert**
   - Full message text
   - Alert styling based on severity

3. **Event Information**
   - Timestamp (with "X ago")
   - Event ID
   - User (name + email if available)
   - IP Address
   - Request Path (with HTTP method)
   - User Agent (truncated)

4. **Metadata** (if present)
   - JSON display (formatted)
   - Syntax highlighted
   - Scrollable

5. **Resolution Form** (if unresolved)
   - Resolution Notes textarea
   - "Mark as Resolved" button

6. **Resolution Information** (if resolved)
   - Resolved At timestamp
   - Resolved By user
   - Resolution Notes

7. **Quick Links Sidebar**
   - Similar Severity Events
   - Same Category Events
   - Same Event Type
   - User's Events (if user present)
   - Same IP Events (if IP present)

8. **Statistics Sidebar**
   - Severity level progress bar
   - Category badge
   - Status badge

### Statistics Page

**URL**: `/referensi/audit/statistics/`

**Charts & Reports:**

1. **90-Day Trend (Line Chart)**
   - Shows daily event count for last 90 days
   - Hover for exact date + count
   - Identifies trends

2. **Top 10 Users (List)**
   - Users with most events
   - Event count badge
   - Click to filter by user

3. **Top 10 IP Addresses (List)**
   - IPs with most events
   - Event count badge
   - Click to filter by IP

4. **Top 15 Event Types (List)**
   - Most common event types
   - Event count badge
   - Scrollable

5. **Event Type Distribution (Bar Chart)**
   - Horizontal bar chart
   - Top 15 event types
   - Shows count per type

6. **Severity vs Category Matrix (Heatmap)**
   - Table showing event count for each severity/category combination
   - Color-coded cells:
     - Gray: 0 events
     - Light blue: 1-9 events
     - Yellow: 10-49 events
     - Red: 50+ events

---

## Maintenance

### Daily Tasks

**Automated (via cron):**
- ✅ Cleanup old logs (2 AM)
- ✅ Generate summaries (hourly)
- ✅ Send alerts (every 15 min)

**Manual:**
- ⚠️ Check dashboard for critical events
- ⚠️ Review unresolved events
- ⚠️ Resolve critical issues

### Weekly Tasks

- Review audit statistics
- Check for unusual patterns
- Verify alert emails working
- Review top users/IPs for anomalies

### Monthly Tasks

- Generate monthly report
- Review retention policies
- Update email recipients if needed
- Check database size

### Database Maintenance

```bash
# Check table sizes
python manage.py dbshell
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE tablename LIKE 'referensi_%'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Vacuum tables (PostgreSQL)
VACUUM ANALYZE referensi_securityauditlog;
VACUUM ANALYZE referensi_auditlogsummary;

# Rebuild indexes (if needed)
REINDEX TABLE referensi_securityauditlog;
```

---

## Troubleshooting

### Issue: Dashboard not loading

**Symptoms**: 500 error or blank page

**Solutions:**
```bash
# 1. Check migrations applied
python manage.py showmigrations referensi

# 2. Check permissions
python manage.py shell
>>> from django.contrib.auth import get_user_model
>>> user = get_user_model().objects.get(username='youruser')
>>> user.has_perm('referensi.view_ahsp_stats')

# 3. Check logs
tail -f logs/django.log
```

### Issue: No audit logs appearing

**Symptoms**: Dashboard shows 0 events

**Solutions:**
```bash
# 1. Verify audit logger integration
python manage.py shell
>>> from referensi.services.audit_logger import audit_logger
>>> log = audit_logger.log_event("test", "Test message")
>>> print(log.id)

# 2. Check database
python manage.py dbshell
SELECT COUNT(*) FROM referensi_securityauditlog;

# 3. Verify audit logger called in code
# Check that views/services call audit_logger.log_*()
```

### Issue: Email alerts not sending

**Symptoms**: No alert emails received

**Solutions:**
```bash
# 1. Check email configuration
python manage.py shell
>>> from django.core.mail import mail_admins
>>> mail_admins("Test", "Test message")

# 2. Check ADMINS configured
python manage.py shell
>>> from django.conf import settings
>>> print(settings.ADMINS)

# 3. Check SMTP settings
>>> print(settings.EMAIL_HOST)
>>> print(settings.EMAIL_PORT)

# 4. Test send_audit_alerts command
python manage.py send_audit_alerts --dry-run
```

### Issue: Dashboard slow

**Symptoms**: Dashboard takes >3 seconds to load

**Solutions:**
```bash
# 1. Generate summaries
python manage.py generate_audit_summary --period=daily --days=30

# 2. Check database indexes
python manage.py dbshell
SELECT indexname, tablename FROM pg_indexes
WHERE tablename = 'referensi_securityauditlog';

# 3. Cleanup old logs
python manage.py cleanup_audit_logs --days=30

# 4. Optimize queries (check DEBUG toolbar)
```

### Issue: CSV export fails

**Symptoms**: Export button doesn't work or timeout

**Solutions:**
```bash
# 1. Reduce date range in filters
# 2. Export is limited to 10,000 rows

# 3. For larger exports, use management command:
python manage.py dbshell
COPY (
    SELECT * FROM referensi_securityauditlog
    WHERE timestamp >= '2025-01-01'
) TO '/tmp/audit_logs.csv' CSV HEADER;
```

---

## Next Steps

### Completing Phase 2 (15% remaining)

To reach 100% completion:

**1. Write Tests (40 tests, ~6-8 hours)**

Create `referensi/tests/test_audit_phase2.py`:
- Audit logger service tests (15 tests)
- Dashboard view tests (12 tests)
- Model tests (8 tests)
- Integration tests (5 tests)

**2. Performance Testing**
- Dashboard load time < 1 second
- Logs list query < 500ms
- Export 10K rows < 5 seconds

**3. Security Review**
- XSS protection in templates
- CSRF tokens present
- Permission checks enforced
- SQL injection prevented

### Phase 3: Database Search

Next phase focuses on PostgreSQL full-text search for 10-100x faster searching.

See: `docs/PHASE_3_IMPLEMENTATION_GUIDE.md`

---

**Document Version**: 1.0
**Last Updated**: 2025-01-05
**Status**: Phase 2 at 85% Complete
