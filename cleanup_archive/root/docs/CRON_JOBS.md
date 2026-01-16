# Scheduled Jobs

## Orphan Cleanup (weekly)
Run the automated cleanup command every Saturday at 23:59 server time.

```cron
59 23 * * 6 cd /path/to/DJANGO_AHSP_PROJECT && . .venv/Scripts/activate && python manage.py cleanup_orphans --all-projects --older-than-days=30 >> logs/cleanup_orphans.log 2>&1
```

- Adjust virtual environment path (`.venv/...`) to match your deployment.
- `--older-than-days=30` ensures only items unused for at least 30 days are deleted; tweak if needed.
- Output is appended to `logs/cleanup_orphans.log` for auditing.

To test manually at any time:

```bash
python manage.py cleanup_orphans --all-projects --older-than-days=30 --dry-run
```
