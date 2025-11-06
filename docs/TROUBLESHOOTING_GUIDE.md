# 🔧 Troubleshooting Guide - DJANGO-AHSP-PROJECT

**Version:** 4.0
**Last Updated:** 2025-11-06

---

## 📋 Quick Reference

| Error Code | Severity | Category | Action |
|------------|----------|----------|--------|
| 1000-1999 | 🟡 Low | Validation | Fix input |
| 3000-3999 | 🟠 Medium | Business Logic | Check data |
| 4000-4999 | 🔴 High | Database | Check integrity |
| 5000-5999 | 🔴🔴 Critical | System | Contact admin |

---

## 🚨 Common Issues & Solutions

### 1. Login & Authentication

#### Issue: Cannot Login
**Symptoms:** Login form shows "Invalid credentials"

**Possible Causes:**
- Wrong username/password
- Account disabled
- Session expired

**Solutions:**
```bash
# Check if user exists
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.filter(username='your_username').exists()

# Reset password
python manage.py changepassword your_username

# Check user is active
>>> user = User.objects.get(username='your_username')
>>> user.is_active
True
```

#### Issue: "CSRF token missing or incorrect"
**Solution:**
1. Clear browser cookies
2. Hard refresh (Ctrl+Shift+R)
3. Check `CSRF_COOKIE_SECURE` in settings matches your HTTPS setup

---

### 2. Dashboard Issues

#### Issue: Dashboard Loads Slowly
**Symptoms:** Page takes >5 seconds to load

**Diagnostics:**
```bash
# Check number of projects
python manage.py shell
>>> from dashboard.models import Project
>>> Project.objects.count()  # If > 10,000, optimize

# Check database queries
pip install django-debug-toolbar
# Enable in settings.py (dev only)
```

**Solutions:**
1. **Use Filters:** Apply filters to reduce dataset
2. **Collapse Analytics:** Hide analytics section if not needed
3. **Pagination:** Ensure pagination is working (default: 10 per page)
4. **Database Indexes:** Run migrations to ensure indexes exist

```sql
-- Check indexes (PostgreSQL)
SELECT indexname FROM pg_indexes WHERE tablename = 'dashboard_project';
```

#### Issue: Charts Not Displaying
**Symptoms:** Analytics section shows but charts are blank

**Solutions:**
1. Check browser console for JavaScript errors (F12)
2. Verify Chart.js CDN is accessible:
   ```html
   https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
   ```
3. Check if data is being passed:
   ```javascript
   console.log(projectsByYearData);  // Should not be empty
   ```
4. Clear browser cache and reload

---

### 3. Project Management

#### Issue: Cannot Create Project
**Error:** "ValidationError: Nama project minimal 3 karakter"

**Solution:**
- Ensure project name is at least 3 characters
- Check all required fields are filled:
  - Nama, Tanggal Mulai, Sumber Dana, Lokasi, Client, Anggaran

#### Issue: Anggaran Format Error
**Error:** "Anggaran owner tidak valid"

**Valid Formats:**
```
✅ 1000000000
✅ 1.000.000.000
✅ Rp 1.000.000.000
✅ 1,000,000,000.00

❌ 1 Miliar (use numbers)
❌ abc123 (no letters)
```

#### Issue: Timeline Validation Error
**Error:** "Tanggal selesai harus setelah tanggal mulai"

**Solution:**
- Ensure `tanggal_selesai > tanggal_mulai`
- Check date format: YYYY-MM-DD or DD/MM/YYYY
- Verify dates are valid (no Feb 30, etc.)

---

### 4. Deep Copy Issues

#### Issue: Deep Copy Fails with Error 3002
**Error:** "SOURCE_PROJECT_INVALID"

**Possible Causes:**
- Project ID doesn't exist
- You're not the owner
- Project was deleted/archived

**Solution:**
```bash
# Verify project exists and you're the owner
python manage.py shell
>>> from dashboard.models import Project
>>> proj = Project.objects.get(pk=123)
>>> proj.owner.username
'your_username'
>>> proj.is_active
True
```

#### Issue: Deep Copy Timeout
**Error:** "Request timeout after 120 seconds"

**Causes:**
- Project too large (>2000 pekerjaan)
- Server overloaded

**Solutions:**
1. **Increase Timeout:**
   ```python
   # gunicorn_config.py
   timeout = 300  # 5 minutes
   ```

2. **Use Async Deep Copy:**
   ```bash
   # Contact admin for bulk copy script
   python manage.py deep_copy_project --project-id=123 --new-name="Copy" --async
   ```

3. **Reduce Scope:**
   - Uncheck unnecessary options (AHSP Template, Tahapan)
   - Copy in stages

#### Issue: Deep Copy with Warnings/Skipped Items
**Warning:** "2 Sub-Klasifikasi skipped, 5 Pekerjaan skipped"

**Explanation:**
- Some items have missing dependencies (orphaned data)
- Deep copy skips these to maintain integrity

**What to Do:**
1. **If skipped count is low (<5%):** Generally safe to ignore
2. **If skipped count is high (>10%):**
   ```bash
   # Check data integrity in original project
   python manage.py check_project_integrity --project-id=123
   ```
3. **Contact admin** if you need these items recovered

---

### 5. Filter & Search Issues

#### Issue: Search Returns No Results
**Check:**
- Search is case-insensitive
- Searches across 6 fields: nama, deskripsi, sumber_dana, lokasi, nama_client, kategori
- Try partial match: "Jalan" instead of "Jalan Raya Protokol"

#### Issue: Filter Not Working
**Symptoms:** Filter applied but shows same results

**Solutions:**
1. **Check URL parameters:**
   ```
   /dashboard/?tahun_project=2025&sumber_dana=APBN
   ```
   Should show in URL after "Apply Filter"

2. **Clear All Filters:** Click "Reset" button

3. **Browser Cache:** Hard refresh (Ctrl+Shift+R)

---

### 6. Export Issues

#### Issue: Excel Export Empty/Corrupt
**Symptoms:** Downloaded file won't open or is empty

**Solutions:**
1. **Check filter:** Ensure filter returns results
2. **Disable antivirus temporarily:** Some AV block .xlsx downloads
3. **Try different browser:** Chrome, Firefox, Edge
4. **Check server logs:**
   ```bash
   tail -f /var/log/django-ahsp/error.log
   ```

#### Issue: CSV Export Shows Garbled Characters
**Problem:** Indonesian characters show as "??????"

**Solution:**
- Use Excel's "Data > From Text/CSV" import feature
- Select "UTF-8" encoding when opening
- Or use LibreOffice Calc (handles UTF-8 BOM automatically)

#### Issue: PDF Export Fails
**Error:** "ReportLab not installed" or "Font error"

**Solution:**
```bash
# Install ReportLab
pip install reportlab

# Check installation
python -c "import reportlab; print(reportlab.Version)"

# If font issues, install fonts
sudo apt-get install -y fonts-liberation
```

---

### 7. Bulk Operations Issues

#### Issue: Bulk Delete Fails
**Error:** "No projects selected" or "No valid projects found"

**Solutions:**
1. **Verify selection:** Ensure checkboxes are checked
2. **User isolation:** You can only delete your own projects
3. **Already deleted:** Check if projects are already archived

```bash
# Check project ownership
python manage.py shell
>>> from dashboard.models import Project
>>> Project.objects.filter(pk__in=[1,2,3], owner__username='yourname')
```

#### Issue: Bulk Export Timeout
**Symptoms:** Export hangs for >2 minutes

**Solutions:**
1. **Reduce selection:** Max 1000 projects at a time
2. **Use filters + export all:** Better than selecting manually
3. **Contact admin** for async bulk export

---

### 8. Admin Panel Issues

#### Issue: Cannot Access Admin Panel
**Error:** 403 Forbidden or "You don't have permission"

**Solution:**
```bash
# Grant admin permission
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username='yourname')
>>> user.is_staff = True
>>> user.is_superuser = True
>>> user.save()
```

#### Issue: Admin List View Empty
**Check:**
1. **Filters active:** Clear sidebar filters
2. **Date hierarchy:** Reset by clicking "All" at top
3. **Search:** Clear search box

---

### 9. Database Issues

#### Issue: "database is locked" (SQLite)
**Error:** OperationalError: database is locked

**Cause:** SQLite doesn't handle concurrent writes

**Solution:**
```python
# Switch to PostgreSQL (recommended for production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # ... config
    }
}
```

#### Issue: "too many connections"
**Error:** OperationalError: FATAL: too many clients already

**Solution:**
```sql
-- Increase max connections (PostgreSQL)
-- Edit postgresql.conf
max_connections = 200

-- Or use connection pooling
DATABASES = {
    'default': {
        'CONN_MAX_AGE': 600,  # 10 minutes
    }
}
```

#### Issue: Migration Fails
**Error:** "django.db.utils.IntegrityError"

**Solutions:**
1. **Check existing data:**
   ```bash
   python manage.py showmigrations
   ```

2. **Fake migration if needed:**
   ```bash
   python manage.py migrate dashboard 0008 --fake
   python manage.py migrate
   ```

3. **Backup and reset:**
   ```bash
   # DANGER: Only if acceptable to lose data
   python manage.py migrate dashboard zero
   python manage.py migrate
   ```

---

### 10. Performance Issues

#### Issue: Slow Queries
**Symptoms:** Dashboard takes >10 seconds to load

**Diagnostics:**
```python
# settings.py (dev only)
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',  # Log all queries
        },
    },
}
```

**Solutions:**
1. **Add indexes:** Ensure migrations are current
2. **Use select_related:** Already implemented in views
3. **Optimize queries:** See [PERFORMANCE_TUNING_GUIDE.md](./PERFORMANCE_TUNING_GUIDE.md)

#### Issue: High Memory Usage
**Symptoms:** Server runs out of memory

**Solutions:**
```python
# Paginate large querysets
queryset = Project.objects.all()[:10]  # Limit

# Use iterator for large datasets
for project in Project.objects.iterator(chunk_size=500):
    process(project)

# Clear query cache periodically
from django import db
db.reset_queries()
```

---

## 🛠️ Debugging Tools

### Enable Debug Mode (Dev Only)

```python
# settings.py
DEBUG = True
ALLOWED_HOSTS = ['*']

# Install Django Debug Toolbar
INSTALLED_APPS += ['debug_toolbar']
MIDDLEWARE.insert(0, 'debug_toolbar.middleware.DebugToolbarMiddleware')
INTERNAL_IPS = ['127.0.0.1']
```

### Check Logs

```bash
# Application logs
tail -f /var/log/django-ahsp/error.log

# Gunicorn logs
tail -f /var/log/django-ahsp/gunicorn-error.log

# Nginx logs
tail -f /var/log/nginx/error.log

# System logs
journalctl -u django-ahsp -f
```

### Database Diagnostics

```sql
-- PostgreSQL: Check slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Django Shell Debugging

```bash
python manage.py shell
>>> from dashboard.models import Project
>>> from django.db import connection
>>> from django.db import reset_queries

# Check query count
>>> reset_queries()
>>> list(Project.objects.all()[:10])
>>> len(connection.queries)  # Should be low (<10)

# Explain query
>>> print(Project.objects.filter(tahun_project=2025).query)
```

---

## 📞 Getting Help

### Before Contacting Support

1. **Check this guide** for common solutions
2. **Collect error information:**
   - Error message/code
   - Error ID (if displayed)
   - Steps to reproduce
   - Screenshot
   - Browser/OS info

3. **Check logs** for additional context

### Contacting Support

**Email:** support@yourdomain.com
**Include:**
- Error ID
- Steps to reproduce
- Expected vs actual behavior
- Screenshots
- Relevant logs

### Emergency Contact

**Critical issues (production down):**
- Phone: +62-XXX-XXXX-XXXX
- Available: 24/7
- Response time: <1 hour

---

## 📚 Related Guides

- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Production setup
- **[User Manual](./USER_MANUAL_ID.md)** - Feature usage
- **[Performance Tuning](./PERFORMANCE_TUNING_GUIDE.md)** - Optimization
- **[Roadmap](./DASHBOARD_IMPROVEMENT_ROADMAP.md)** - Features & status

---

**Last Updated:** 2025-11-06
**Version:** 4.0
