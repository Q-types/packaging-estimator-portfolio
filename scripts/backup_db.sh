#!/bin/bash
# Database backup script for KSP Packaging Estimator
# Usage: ./scripts/backup_db.sh [backup_dir]
#
# Requires POSTGRES_USER, POSTGRES_DB, POSTGRES_HOST, POSTGRES_PORT
# environment variables or .env file.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env if present
if [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Configuration
DB_USER="${POSTGRES_USER:-ksp}"
DB_NAME="${POSTGRES_DB:-ksp_estimator}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
BACKUP_DIR="${1:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/${DB_NAME}_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

echo "=== KSP Database Backup ==="
echo "Database: $DB_NAME@$DB_HOST:$DB_PORT"
echo "Backup to: $BACKUP_FILE"
echo "Retention: $RETENTION_DAYS days"
echo ""

# Run backup
if command -v docker &> /dev/null && docker compose ps db &> /dev/null 2>&1; then
    echo "Using Docker container for pg_dump..."
    docker compose exec -T db pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-privileges \
        --verbose 2>/dev/null | gzip > "$BACKUP_FILE"
else
    echo "Using local pg_dump..."
    PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-privileges \
        --verbose 2>/dev/null | gzip > "$BACKUP_FILE"
fi

# Verify backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "Backup complete: $BACKUP_FILE ($BACKUP_SIZE)"

# Prune old backups
DELETED=$(find "$BACKUP_DIR" -name "${DB_NAME}_*.sql.gz" -mtime +"$RETENTION_DAYS" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "Pruned $DELETED backup(s) older than $RETENTION_DAYS days"
fi

# List recent backups
echo ""
echo "Recent backups:"
ls -lht "$BACKUP_DIR"/${DB_NAME}_*.sql.gz 2>/dev/null | head -5

echo ""
echo "=== Backup complete ==="
