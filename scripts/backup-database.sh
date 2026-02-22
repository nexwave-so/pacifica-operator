#!/bin/bash
# PostgreSQL Backup Script for Nexwave
# Performs automated database backups with rotation

set -e

# Configuration
BACKUP_DIR="/var/www/nexwave/backups/postgres"
CONTAINER_NAME="nexwave-postgres"
DB_NAME="nexwave"
DB_USER="nexwave"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="nexwave_backup_${TIMESTAMP}.sql.gz"
KEEP_BACKUPS=7  # Keep last 7 backups

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

echo "Starting PostgreSQL backup at $(date)"

# Perform backup using pg_dump
docker exec -t ${CONTAINER_NAME} pg_dump -U ${DB_USER} -d ${DB_NAME} \
  --format=plain \
  --no-owner \
  --no-acl \
  --verbose \
  | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    echo "✅ Backup completed successfully: ${BACKUP_FILE}"
    BACKUP_SIZE=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
    echo "   Size: ${BACKUP_SIZE}"
else
    echo "❌ Backup failed!"
    exit 1
fi

# Rotate old backups (keep only last N backups)
echo "Rotating old backups (keeping last ${KEEP_BACKUPS})..."
cd "${BACKUP_DIR}"
ls -t nexwave_backup_*.sql.gz | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -v

# Show remaining backups
echo ""
echo "Current backups:"
ls -lh "${BACKUP_DIR}"/nexwave_backup_*.sql.gz 2>/dev/null || echo "No backups found"

echo ""
echo "Backup completed at $(date)"
