#!/bin/bash
# Setup SSL certificates for nexwave.so using Let's Encrypt

set -e

DOMAIN="nexwave.so"
EMAIL="fode@alchemexlabs.com"
NGINX_CONTAINER="nexwave-nginx"
PROJECT_NAME="nexwave"

echo "=========================================="
echo "Setting up SSL certificates for ${DOMAIN}"
echo "=========================================="

# Get the full volume names from docker-compose
CERTBOT_DATA_VOLUME="${PROJECT_NAME}_certbot_data"
CERTBOT_WWW_VOLUME="${PROJECT_NAME}_certbot_www"

# Start nginx without SSL first (for certbot challenge)
echo "Starting nginx container..."
cd "$(dirname "$0")/.."
docker-compose up -d nginx

# Wait for nginx to be ready
echo "Waiting for nginx to be ready..."
sleep 10

# Check if nginx is running
if ! docker ps | grep -q ${NGINX_CONTAINER}; then
    echo "Error: NGINX container is not running!"
    docker logs ${NGINX_CONTAINER}
    exit 1
fi

# Verify DNS is pointing to this server
echo "Verifying DNS configuration..."
SERVER_IP=$(curl -s ifconfig.me)
DNS_IP=$(nslookup ${DOMAIN} | grep -A 1 "Name:" | tail -1 | awk '{print $2}' || echo "")

if [ -n "$DNS_IP" ] && [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo "Warning: DNS may not be pointing to this server!"
    echo "Server IP: ${SERVER_IP}"
    echo "DNS IP: ${DNS_IP}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Run certbot to obtain certificates
echo "Requesting SSL certificates from Let's Encrypt..."
docker run --rm \
  -v ${CERTBOT_DATA_VOLUME}:/etc/letsencrypt \
  -v ${CERTBOT_WWW_VOLUME}:/var/www/certbot \
  certbot/certbot \
  certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email ${EMAIL} \
  --agree-tos \
  --no-eff-email \
  --preferred-challenges http \
  -d ${DOMAIN} \
  -d www.${DOMAIN}

if [ $? -eq 0 ]; then
    echo ""
    echo "SSL certificates obtained successfully!"
    
    # Restart nginx to use SSL certificates
    echo "Restarting nginx with SSL configuration..."
    docker-compose restart nginx
    
    echo ""
    echo "=========================================="
    echo "SSL setup complete!"
    echo "Your site is now accessible at:"
    echo "  - https://${DOMAIN}"
    echo "  - https://www.${DOMAIN}"
    echo "=========================================="
else
    echo "Error: Failed to obtain SSL certificates"
    echo "Please check the error messages above"
    exit 1
fi

