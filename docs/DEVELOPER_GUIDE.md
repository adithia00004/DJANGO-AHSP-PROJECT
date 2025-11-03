# Developer Guide

## Environment

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and adjust database credentials if required.
3. Apply migrations:
   ```bash
   python manage.py migrate
   python manage.py createcachetable
   ```

## Running the Project

```bash
python manage.py runserver
```

The Referensi app is accessible via `/referensi/admin-portal/` once you have a staff user with the `Referensi Editor` or `Referensi Admin` group.

## Testing & Coverage

```bash
pytest
```

The default pytest configuration enforces `--cov=referensi` with a minimum coverage of 80%. Coverage reports are printed to the terminal; add `--cov-report=html` for an HTML report.

### Useful Markers

- `pytest -k preview` – run only preview-related tests
- `pytest --no-cov` – disable coverage when debugging a specific test

## Linting / Formatting

At the moment no formal linting pipeline is configured. The project follows Django best practices with 120-character line width. When contributing, prefer:
- Docstrings in Google style
- Meaningful helper names (see `referensi/services/*`)

## Management Commands

- `python manage.py warm_cache` – pre-warm Referensi dropdown caches
- `python manage.py refresh_stats` – refresh materialized statistics view

## Data Import Workflow

1. Log in as a user with `import_ahsp_data` permission.
2. Visit `/referensi/import/preview/` to upload Excel files.
3. Adjust entries inline; changes persist in the temporary preview session.
4. Submit to commit data; audit history is recorded automatically.

## Permission Matrix

Refer to `docs/PERMISSIONS.md` for detailed group breakdown. Assign users to the appropriate group after creation to unlock module access.
