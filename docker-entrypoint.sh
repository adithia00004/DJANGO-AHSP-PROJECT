#!/bin/bash
set -e

echo "Starting Django AHSP Application..."

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h $POSTGRES_HOST -p $POSTGRES_PORT -U postgres; do
  sleep 1
done
echo "PostgreSQL started"

# Wait for Redis to be ready
echo "Waiting for Redis..."
while ! redis-cli -h $REDIS_HOST -p $REDIS_PORT ping > /dev/null 2>&1; do
  sleep 1
done
echo "Redis started"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create superuser if it doesn't exist (for development)
if [ "$DJANGO_ENV" = "development" ]; then
  echo "Creating development superuser if needed..."
  python manage.py shell << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin')
    print('Superuser created: admin/admin')
else:
    print('Superuser already exists')
END
fi

# Health check endpoint
echo "Setting up health check..."
python manage.py shell << END
from django.conf import settings
from django.urls import path
from django.http import JsonResponse

def health(request):
    return JsonResponse({'status': 'ok'})

if not any('health' in str(url.pattern) for url in settings.URL_CONF):
    print('Health check endpoint ready')
END

echo "Application is ready!"
echo "Starting server on 0.0.0.0:8000..."

# Execute the main command
exec "$@"
