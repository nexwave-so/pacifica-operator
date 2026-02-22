#!/bin/bash
# Renew SSL certificates for nexwave.so

set -e

DOMAIN="nexwave.so"
NGINX_CONTAINER="nexwave-nginx"
PROJECT_NAME="nexwave"

# Get the full volume names from docker-compose
CERTBOT_DATA_VOLUME="${PROJECT_NAME}_certbot_data"
CERTBOT_WWW_VOLUME="${PROJECT_NAME}_certbot_www"

echo "Renewing SSL certificates for ${DOMAIN}..."

# Change to project directory
cd "$(dirname "$0")/.."

# Renew certificates
docker run --rm \
  -v ${CERTBOT_DATA_VOLUME}:/etc/letsencrypt \
  -v ${CERTBOT_WWW_VOLUME}:/var/www/certbot \
  certbot/certbot \
  renew \
  --quiet

# Check if certificates were renewed
if [ $? -eq 0 ]; then
    # Reload nginx to use renewed certificates
    echo "Reloading nginx..."
    docker exec ${NGINX_CONTAINER} nginx -s reload
    
    if [ $? -eq 0 ]; then
        echo "SSL certificates renewed successfully!"
    else
        echo "Warning: Failed to reload nginx, but certificates were renewed"
        echo "You may need to restart nginx manually: docker-compose restart nginx"
    fi
else
    echo "No certificates were renewed (may not be due yet)"
fi

