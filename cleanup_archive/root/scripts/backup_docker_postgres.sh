#!/bin/bash

# Setup Timestamp (YYYYMMDD_HHMMSS)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="backup_ahsp_docker_${TIMESTAMP}.sql"

echo "=========================================="
echo "      BACKUP POSTGRESQL DOCKER TO SQL"
echo "=========================================="
echo ""
echo "[1/2] Checking database container..."

# Check if container is running
if ! docker ps | grep -q "ahsp_postgres"; then
    echo "[ERROR] Container 'ahsp_postgres' is NOT running."
    echo "Please run 'docker-compose up -d db' first."
    exit 1
fi

echo "[2/2] Exporting database (pg_dump)..."
echo "      Target File: ${FILENAME}"

# Run pg_dump
# MSYS_NO_PATHCONV=1 is crucial for Git Bash on Windows to prevent path conversion issues
MSYS_NO_PATHCONV=1 docker exec -t ahsp_postgres pg_dump -U postgres --clean --if-exists ahsp_sni_db > "${FILENAME}"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "      BACKUP SUCCESSFUL!"
    echo "=========================================="
    echo "Files saved at: $(pwd)/${FILENAME}"
else
    echo ""
    echo "[ERROR] Backup process failed."
    rm -f "${FILENAME}" # Clean up empty file if failed
    exit 1
fi
