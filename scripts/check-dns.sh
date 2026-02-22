#!/bin/bash
# DNS Propagation Checker for nexwave.so

TARGET_IP="206.189.92.214"
DOMAIN="nexwave.so"

echo "=========================================="
echo "DNS Propagation Checker"
echo "=========================================="
echo "Target IP: $TARGET_IP"
echo "Domain: $DOMAIN"
echo ""

# Check local DNS
echo "1. Checking Local DNS..."
LOCAL_IP=$(nslookup $DOMAIN | grep -A 1 "Name:" | tail -1 | awk '{print $2}')
if [ "$LOCAL_IP" == "$TARGET_IP" ]; then
    echo "   ✅ Local DNS: $LOCAL_IP (CORRECT)"
else
    echo "   ⏳ Local DNS: $LOCAL_IP (waiting for propagation)"
fi

# Check Google DNS
echo ""
echo "2. Checking Google DNS (8.8.8.8)..."
GOOGLE_IP=$(dig +short $DOMAIN @8.8.8.8 | tail -1)
if [ "$GOOGLE_IP" == "$TARGET_IP" ]; then
    echo "   ✅ Google DNS: $GOOGLE_IP (CORRECT)"
else
    echo "   ⏳ Google DNS: $GOOGLE_IP (waiting for propagation)"
fi

# Check Cloudflare DNS
echo ""
echo "3. Checking Cloudflare DNS (1.1.1.1)..."
CF_IP=$(dig +short $DOMAIN @1.1.1.1 | tail -1)
if [ "$CF_IP" == "$TARGET_IP" ]; then
    echo "   ✅ Cloudflare DNS: $CF_IP (CORRECT)"
else
    echo "   ⏳ Cloudflare DNS: $CF_IP (waiting for propagation)"
fi

echo ""
echo "=========================================="
if [ "$LOCAL_IP" == "$TARGET_IP" ] && [ "$GOOGLE_IP" == "$TARGET_IP" ] && [ "$CF_IP" == "$TARGET_IP" ]; then
    echo "✅ DNS FULLY PROPAGATED!"
    echo "You can now run: ./scripts/setup-ssl.sh"
else
    echo "⏳ DNS still propagating... Try again in a few minutes"
    echo "Tip: Run 'watch -n 30 ./scripts/check-dns.sh' to monitor"
fi
echo "=========================================="
