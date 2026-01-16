# Database Backup Guide

## Quick Commands

### PostgreSQL Backup
```bash
# Full database backup
pg_dump -h localhost -U postgres -d ahsp_db -F c -f backup_$(date +%Y%m%d_%H%M%S).dump

# With compression
pg_dump -h localhost -U postgres -d ahsp_db -Z 9 > backup_$(date +%Y%m%d).sql.gz
```

### PostgreSQL Restore
```bash
# From custom format
pg_restore -h localhost -U postgres -d ahsp_db -c backup_20260107.dump

# From SQL
psql -h localhost -U postgres -d ahsp_db < backup_20260107.sql
```

---

## Backup Strategy

### Daily Backups
- **Recommended:** Every night at 2:00 AM
- **Retention:** Keep 7 daily backups

### Weekly Backups
- **Recommended:** Every Sunday
- **Retention:** Keep 4 weekly backups

### Monthly Backups
- **Recommended:** First day of month
- **Retention:** Keep 12 monthly backups

---

## Cron Schedule Example

```bash
# Daily at 2:00 AM
0 2 * * * pg_dump -h localhost -U postgres -d ahsp_db -F c -f /backups/daily/backup_$(date +\%Y\%m\%d).dump

# Weekly on Sunday at 3:00 AM
0 3 * * 0 pg_dump -h localhost -U postgres -d ahsp_db -F c -f /backups/weekly/backup_$(date +\%Y\%m\%d).dump

# Monthly on 1st at 4:00 AM
0 4 1 * * pg_dump -h localhost -U postgres -d ahsp_db -F c -f /backups/monthly/backup_$(date +\%Y\%m).dump
```

---

## Media Files Backup

```bash
# Backup uploaded files
tar -czvf media_backup_$(date +%Y%m%d).tar.gz /path/to/media/

# Sync to remote (rsync)
rsync -avz /path/to/media/ user@backup-server:/backups/media/
```

---

## Verification

Always verify backups can be restored:

```bash
# Create test database
createdb -h localhost -U postgres ahsp_test

# Restore backup
pg_restore -h localhost -U postgres -d ahsp_test backup.dump

# Run quick verification
psql -h localhost -U postgres -d ahsp_test -c "SELECT COUNT(*) FROM detail_project_pekerjaan;"

# Cleanup
dropdb -h localhost -U postgres ahsp_test
```

---

## Cloud Options

- **AWS RDS:** Automated daily backups
- **Digital Ocean:** Weekly snapshots
- **Managed PostgreSQL:** Built-in PITR (Point-in-Time Recovery)
