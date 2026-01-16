# Database Tuning Checklist

## Routine Maintenance

```sql
-- Refresh query planner statistics
ANALYZE referensi_ahspreferensi;
ANALYZE referensi_rincianreferensi;
ANALYZE referensi_kode_item;
ANALYZE referensi_ahsp_stats;
```

Run after bulk imports or nightly via cron.

## Recommended postgresql.conf overrides

```
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 16MB
maintenance_work_mem = 128MB
wal_compression = on
```

Adjust based on available memory (target 25% RAM for `shared_buffers`).

## Connection Pooling

- Deploy PgBouncer in transaction pooling mode.
- Update `DATABASES["default"]["CONN_MAX_AGE"]` to a lower value (e.g., 120) when pooling.

## Backup Strategy

- Nightly `pg_dump` stored in encrypted object storage.
- Weekly base backup using `pg_basebackup`.
- Retain at least 7 daily + 4 weekly snapshots.
- Test restore quarterly.

## Pre-deployment Checklist

- [ ] Confirm `ANALYZE` run within last 24h.
- [ ] Verify replication/backup jobs succeeded (check monitoring dashboards).
- [ ] Ensure connection limits in PgBouncer accommodate web + worker processes.
