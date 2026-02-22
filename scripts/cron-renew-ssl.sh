#!/bin/bash
# Cron script for automatic SSL certificate renewal
# Add this to crontab: 0 3 * * * /var/www/nexwave/scripts/cron-renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1

/var/www/nexwave/scripts/renew-ssl.sh

