# Quick Start: NGINX & SSL Setup

## Prerequisites Checklist

Before setting up SSL, ensure:

- [ ] Domain `nexwave.so` DNS A record points to your server IP
- [ ] Ports 80 and 443 are open in firewall (`sudo ufw allow 80,443` or equivalent)
- [ ] Docker and Docker Compose are installed
- [ ] You have root/sudo access to the server

## Quick Setup (3 Steps)

### Step 1: Start Services

```bash
cd /var/www/nexwave
docker compose up -d --remove-orphans
```

### Step 2: Obtain SSL Certificates

```bash
./scripts/setup-ssl.sh
```

This will:
- Start NGINX
- Verify DNS configuration
- Request Let's Encrypt certificates
- Configure NGINX with SSL
- Restart services

### Step 3: Verify

Visit `https://nexwave.so` - you should see the site with a valid SSL certificate!

## What's Configured

✅ **NGINX Reverse Proxy**:
- Frontend: `https://nexwave.so/` → Next.js (port 3000)
- API: `https://nexwave.so/api/*` → FastAPI (port 8000)
- WebSocket: `https://nexwave.so/ws/*` → FastAPI WebSocket

✅ **SSL Certificates**:
- Automatic Let's Encrypt certificates
- Auto-renewal setup (run `./scripts/renew-ssl.sh` or set up cron)

✅ **Security Headers**:
- HSTS (HTTP Strict Transport Security)
- X-Frame-Options
- X-Content-Type-Options
- X-XSS-Protection

## Automatic Renewal

Set up cron for automatic certificate renewal:

```bash
crontab -e
# Add this line (runs daily at 3 AM):
0 3 * * * /var/www/nexwave/scripts/cron-renew-ssl.sh >> /var/log/ssl-renewal.log 2>&1
```

## Troubleshooting

**Certificates not obtained?**
- Check DNS: `nslookup nexwave.so`
- Check firewall: `sudo ufw status`
- Check NGINX logs: `docker logs nexwave-nginx`

**Need help?**
See `NGINX_SETUP.md` for detailed documentation.

