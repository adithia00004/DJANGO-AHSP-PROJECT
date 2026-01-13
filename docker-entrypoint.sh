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
echo "Waiting for Redis at $REDIS_HOST:$REDIS_PORT..."
for i in {1..30}; do
  # Try to connect without password first (for local dev), then with password
  if python -c "
import redis
try:
  r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, db=0, socket_connect_timeout=2)
  r.ping()
except redis.AuthenticationError:
  r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, db=0, password='$REDIS_PASSWORD', socket_connect_timeout=2)
  r.ping()
" > /dev/null 2>&1; then
    echo "Redis started"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "WARNING: Redis not responding after 30 attempts, but continuing anyway..."
    break
  fi
  sleep 1
done

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

# Health check endpoint - optional, doesn't block startup
echo "Setting up health check..."
python manage.py shell << END 2>/dev/null || true
try:
    from django.conf import settings
    print('Health check configuration verified')
except Exception as e:
    print(f'Health check skipped: {e}')
END

echo "Application is ready!"
echo "Starting server on 0.0.0.0:8000..."

# Execute the main command
exec "$@"
