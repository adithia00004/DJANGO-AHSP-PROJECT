# Deployment Checklist

## Pre-Deployment

- [ ] `python manage.py check --deploy`
- [ ] `python manage.py showmigrations --plan`
- [ ] Confirm `.env.production` matches `.env.production.example`
- [ ] Ensure database backups succeeded within last 24 hours
- [ ] `DJANGO_ENV=production python manage.py collectstatic --noinput`
- [ ] `DJANGO_ENV=production pytest --no-cov`

## Staging

- [ ] Deploy to staging environment
- [ ] Run smoke tests (login, import preview, search)
- [ ] Review slow request logs

## Production Rollout

- [ ] Schedule deployment during low traffic window
- [ ] Take fresh database snapshot/backup
- [ ] Deploy code & run migrations
- [ ] Warm caches: `python manage.py warm_cache`
- [ ] Refresh materialized view: `python manage.py refresh_stats`
- [ ] Monitor logs and metrics for 24 hours

## Rollback Plan

- Restore latest database backup
- Re-deploy previous application build
- Disable new feature toggles if applicable
