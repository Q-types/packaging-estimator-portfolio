#!/bin/bash
# Database restore script for KSP Packaging Estimator
# Usage: ./scripts/restore_db.sh <backup_file.sql.gz>
#
# WARNING: This will drop and recreate the database!

set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
    ls -lht "$PROJECT_DIR/backups/"*.sql.gz 2>/dev/null | head -10 || echo "  No backups found in $PROJECT_DIR/backups/"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

DB_USER="${POSTGRES_USER:-ksp}"
DB_NAME="${POSTGRES_DB:-ksp_estimator}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

echo "=== KSP Database Restore ==="
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "From: $BACKUP_FILE"
echo ""
echo "WARNING: This will DROP and RECREATE the database '$DB_NAME'!"
read -p "Are you sure? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

if command -v docker &> /dev/null && docker compose ps db &> /dev/null 2>&1; then
    echo "Using Docker container..."
    # Drop and recreate
    docker compose exec -T db psql -U "$DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME;" \
        -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    # Restore
    gunzip -c "$BACKUP_FILE" | docker compose exec -T db psql -U "$DB_USER" -d "$DB_NAME" --quiet
else
    echo "Using local psql..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres \
        -c "DROP DATABASE IF EXISTS $DB_NAME;" \
        -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"
    gunzip -c "$BACKUP_FILE" | PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" --quiet
fi

echo ""
echo "=== Restore complete ==="
