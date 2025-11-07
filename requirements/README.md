# Requirements Documentation

This directory contains environment-specific requirements files for the AHSP project.

## File Structure

```
requirements/
├── README.md           # This file
├── base.txt           # Base dependencies (all environments)
├── development.txt    # Development tools & testing
├── staging.txt        # Staging environment
└── production.txt     # Production environment
```

## Installation

### Development Environment

For local development with all dev tools:

```bash
pip install -r requirements/development.txt
```

This includes:
- Base Django packages
- Django Debug Toolbar
- Testing frameworks (pytest, coverage)
- Code quality tools (black, flake8, pylint)
- Development utilities (ipython, ipdb)

### Staging Environment

For staging deployment (mirrors production with extra testing tools):

```bash
pip install -r requirements/staging.txt
```

This includes:
- Base packages
- Gunicorn WSGI server
- Monitoring tools
- Testing frameworks
- Performance profiling

### Production Environment

For production deployment:

```bash
pip install -r requirements/production.txt
```

This includes:
- Base packages (Django, Redis, PostgreSQL)
- Gunicorn WSGI server
- Sentry error tracking
- Celery for async tasks
- Production utilities

## Dependencies Summary

### Core Dependencies (base.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| Django | 5.2.4 | Web framework |
| django-allauth | 65.10.0 | Authentication |
| psycopg2-binary | 2.9.10 | PostgreSQL adapter |
| redis | 5.2.1 | Redis client |
| django-redis | 5.4.0 | Redis cache backend |
| gunicorn | 22.0.0 | WSGI server (prod/staging) |
| celery | 5.4.0 | Async task queue (prod/staging) |

### Key Features by Environment

#### Development
- Django Debug Toolbar for SQL query analysis
- pytest for testing
- black/flake8 for code quality
- ipython/ipdb for debugging

#### Staging
- Same as production, plus:
  - Testing frameworks for CI/CD
  - Performance profiling tools
  - Debug toolbar (selective)

#### Production
- Gunicorn for WSGI serving
- Sentry for error tracking
- Celery for background tasks
- Flower for task monitoring
- Enhanced health checks

## Version Control

**IMPORTANT:**
- The `requirements/` directory should be committed to git
- Individual `.txt` files should be version controlled
- Pin all versions for reproducible builds

## Updating Dependencies

### Check for outdated packages

```bash
pip list --outdated
```

### Update specific package

```bash
# Update in the appropriate requirements file
pip install --upgrade <package-name>
pip freeze | grep <package-name>
# Update version in requirements/*.txt
```

### Security updates

```bash
# Check for security vulnerabilities
pip-audit

# Or use safety
pip install safety
safety check -r requirements/production.txt
```

## Creating Virtual Environments

### Development

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements/development.txt
```

### Production/Staging

```bash
# Use system Python or pyenv for specific version
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt
```

## Docker Usage

For containerized deployments, requirements are used in Dockerfile:

```dockerfile
# Development
FROM python:3.12
COPY requirements/development.txt .
RUN pip install -r development.txt

# Production
FROM python:3.12-slim
COPY requirements/production.txt .
RUN pip install --no-cache-dir -r production.txt
```

## Dependency Notes

### Redis Cache (CRITICAL)

- **Required for production**: Rate limiting won't work without Redis
- Default Django cache (locmem) is **NOT compatible** with multiple workers
- Install Redis: `docker run -d -p 6379:6379 redis:7-alpine`
- See `DEPLOYMENT_GUIDE.md` for full setup

### PostgreSQL

- Development: Local PostgreSQL server
- Production: PostgreSQL 12+ with connection pooling
- Ensure `psycopg2-binary` is installed

### Gunicorn

- Production WSGI server (replaces Django dev server)
- Configuration: `gunicorn.conf.py`
- Workers: `(2 x CPU cores) + 1`

### Celery

- Optional for Phase 5 (async tasks)
- Required for background jobs (batch copy, exports)
- Requires Redis as message broker

## Troubleshooting

### `psycopg2-binary` installation fails

**Solution:**
```bash
# Install PostgreSQL dev headers
# Ubuntu/Debian
sudo apt-get install libpq-dev python3-dev

# macOS
brew install postgresql
```

### `redis` or `hiredis` installation fails

**Solution:**
```bash
# Install build tools
# Ubuntu/Debian
sudo apt-get install build-essential

# macOS
xcode-select --install
```

### `Pillow` installation fails

**Solution:**
```bash
# Install image libraries
# Ubuntu/Debian
sudo apt-get install libjpeg-dev zlib1g-dev

# macOS
brew install jpeg
```

## Best Practices

1. **Always use virtual environments** - Isolate project dependencies
2. **Pin all versions** - Reproducible builds across environments
3. **Test updates in staging first** - Never update production directly
4. **Run security audits regularly** - Use `pip-audit` or `safety`
5. **Document breaking changes** - Update this README when major updates occur

## Migration from Root requirements.txt

If you previously used `/requirements.txt`:

```bash
# Backup old requirements
cp requirements.txt requirements.txt.bak

# For development
pip install -r requirements/development.txt

# Verify
pip freeze > installed.txt
diff requirements.txt.bak installed.txt
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: |
    pip install -r requirements/development.txt

- name: Run tests
  run: pytest
```

### GitLab CI Example

```yaml
# .gitlab-ci.yml
test:
  before_script:
    - pip install -r requirements/development.txt
  script:
    - pytest --cov
```

## Support

For issues related to dependencies:
1. Check this README first
2. Review `DEPLOYMENT_GUIDE.md` for production setup
3. Check individual package documentation
4. Open an issue with environment details

---

**Last Updated:** 2025-11-07
**Maintainer:** Development Team
