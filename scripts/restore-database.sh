#!/bin/bash
# PostgreSQL Restore Script for Nexwave
# Restores database from backup file

set -e

# Configuration
BACKUP_DIR="/var/www/nexwave/backups/postgres"
CONTAINER_NAME="nexwave-postgres"
DB_NAME="nexwave"
DB_USER="nexwave"

# Check if backup file is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "${BACKUP_DIR}"/nexwave_backup_*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Check if file exists
if [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo "❌ Backup file not found: ${BACKUP_DIR}/${BACKUP_FILE}"
    exit 1
fi

echo "⚠️  WARNING: This will DROP and RECREATE the database!"
echo "   Backup file: ${BACKUP_FILE}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Restore cancelled."
    exit 0
fi

echo ""
echo "Starting database restore at $(date)"

# Drop existing database and recreate
echo "Dropping existing database..."
docker exec -t ${CONTAINER_NAME} psql -U ${DB_USER} -d postgres -c "DROP DATABASE IF EXISTS ${DB_NAME};"
docker exec -t ${CONTAINER_NAME} psql -U ${DB_USER} -d postgres -c "CREATE DATABASE ${DB_NAME};"

# Restore from backup
echo "Restoring from backup..."
gunzip -c "${BACKUP_DIR}/${BACKUP_FILE}" | docker exec -i ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME}

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Database restored successfully from ${BACKUP_FILE}"

    # Show table count
    TABLE_COUNT=$(docker exec -t ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -c "\dt" | grep -c "public |" || echo "0")
    echo "   Tables restored: ${TABLE_COUNT}"

    # Show tick count
    TICK_COUNT=$(docker exec -t ${CONTAINER_NAME} psql -U ${DB_USER} -d ${DB_NAME} -tAc "SELECT COUNT(*) FROM ticks;" 2>/dev/null || echo "N/A")
    echo "   Ticks restored: ${TICK_COUNT}"
else
    echo "❌ Restore failed!"
    exit 1
fi

echo ""
echo "Restore completed at $(date)"
echo ""
echo "⚠️  Remember to restart services: docker compose restart"
