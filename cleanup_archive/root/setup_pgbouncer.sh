#!/bin/bash
# PgBouncer Setup Script for Linux/WSL
# This script sets up PgBouncer using Docker

echo "========================================"
echo "PgBouncer Setup for Django AHSP Project"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed or not in PATH"
    echo "Please install Docker from: https://docs.docker.com/get-docker/"
    exit 1
fi

echo "[1/5] Docker detected successfully"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    if [ -f ".env.pgbouncer" ]; then
        echo "[2/5] Copying .env.pgbouncer to .env"
        cp .env.pgbouncer .env
        echo ""
        echo "IMPORTANT: Please edit .env and set your POSTGRES_PASSWORD"
        echo "Then run this script again."
        exit 0
    else
        echo "ERROR: .env.pgbouncer file not found"
        echo "Please create .env file with POSTGRES_PASSWORD"
        exit 1
    fi
fi

echo "[2/5] Environment file (.env) found"
echo ""

# Check if PostgreSQL password is set
if grep -q "POSTGRES_PASSWORD=your_postgres_password_here" .env; then
    echo "ERROR: Please update POSTGRES_PASSWORD in .env file"
    echo "It's currently set to the default value"
    exit 1
fi

echo "[3/5] PostgreSQL password configured"
echo ""

# Stop existing PgBouncer container if running
echo "[4/5] Stopping existing PgBouncer container (if any)..."
docker stop ahsp_pgbouncer 2>/dev/null || true
docker rm ahsp_pgbouncer 2>/dev/null || true
echo ""

# Start PgBouncer using docker-compose
echo "[5/5] Starting PgBouncer container..."
docker-compose -f docker-compose-pgbouncer.yml up -d

if [ $? -ne 0 ]; then
    echo ""
    echo "ERROR: Failed to start PgBouncer container"
    echo "Please check the error messages above"
    exit 1
fi

echo ""
echo "========================================"
echo "PgBouncer Started Successfully!"
echo "========================================"
echo ""
echo "PgBouncer is now running on port 6432"
echo ""
echo "Next steps:"
echo "1. Set PGBOUNCER_PORT=6432 in your .env file"
echo "2. Run: python verify_pgbouncer.py"
echo "3. Restart Django: python manage.py runserver"
echo ""
echo "To view PgBouncer logs:"
echo "  docker logs ahsp_pgbouncer"
echo ""
echo "To stop PgBouncer:"
echo "  docker-compose -f docker-compose-pgbouncer.yml down"
echo ""
