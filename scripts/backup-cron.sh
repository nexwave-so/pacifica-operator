#!/bin/bash
# Setup cron job for automated database backups
# Run this script to install the cron job

SCRIPT_DIR="/var/www/nexwave/scripts"
CRON_SCHEDULE="0 */6 * * *"  # Every 6 hours

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup-database.sh"; then
    echo "✅ Backup cron job already exists"
    echo ""
    echo "Current cron jobs:"
    crontab -l | grep backup-database.sh
else
    # Add cron job
    (crontab -l 2>/dev/null; echo "${CRON_SCHEDULE} ${SCRIPT_DIR}/backup-database.sh >> /var/log/nexwave-backup.log 2>&1") | crontab -

    if [ $? -eq 0 ]; then
        echo "✅ Backup cron job installed successfully"
        echo "   Schedule: Every 6 hours"
        echo "   Log file: /var/log/nexwave-backup.log"
    else
        echo "❌ Failed to install cron job"
        exit 1
    fi
fi

echo ""
echo "To view backup logs: tail -f /var/log/nexwave-backup.log"
echo "To list cron jobs: crontab -l"
echo "To remove cron job: crontab -e (then delete the line)"
