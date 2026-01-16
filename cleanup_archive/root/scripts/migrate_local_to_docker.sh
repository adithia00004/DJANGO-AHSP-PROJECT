#!/bin/bash

echo "=========================================="
echo "     MIGRATE LOCAL DATABASE TO DOCKER"
echo "=========================================="

# 1. Check Docker
if ! docker ps | grep -q "ahsp_web"; then
    echo "[ERROR] Container 'ahsp_web' is not running."
    echo "Please run 'docker-compose up -d' first."
    exit 1
fi

# 2. Dump local DB
echo ""
echo "[1/4] Dumping local database..."
# Force POSTGRES_HOST to localhost to prevent DNS errors (if .env uses 'db' or 'ahsp_postgres')
export POSTGRES_HOST=127.0.0.1
python manage.py dumpdata --natural-foreign --natural-primary \
    --exclude contenttypes \
    --exclude auth.permission \
    --exclude admin.logentry \
    --exclude sessions.session \
    --indent 2 -o full_export.json

if [ $? -ne 0 ]; then
    echo "[ERROR] Dump failed."
    exit 1
fi
echo "[OK] Data extracted to 'full_export.json'."

# 3. Copy to container
echo ""
echo "[2/4] Copying to Docker container..."
MSYS_NO_PATHCONV=1 docker cp full_export.json ahsp_web:/app/full_export.json
if [ $? -ne 0 ]; then
    echo "[ERROR] Copy failed."
    exit 1
fi

# 4. Load data
echo ""
echo "[3/4] Cleaning old Docker DB..."
read -p "Do you want to FLUSH (delete all) data in Docker before import? (y/n): " confirm
if [[ $confirm == [yY] || $confirm == [yY][eE][sS] ]]; then
    MSYS_NO_PATHCONV=1 docker exec -it ahsp_web python manage.py flush --no-input
    echo "[OK] Docker DB cleaned."
else
    echo "[INFO] Skipping flush. Data will be merged."
fi

echo ""
echo "[4/4] Importing data to Docker..."
MSYS_NO_PATHCONV=1 docker exec -it ahsp_web python manage.py loaddata full_export.json
if [ $? -ne 0 ]; then
    echo "[ERROR] Import failed."
    exit 1
fi

echo ""
echo "=========================================="
echo "     MIGRATION SUCCESSFUL!"
echo "=========================================="
rm full_export.json
