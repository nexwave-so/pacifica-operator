#!/bin/bash
# Full raw log stream - shows all trading engine activity

clear
echo "════════════════════════════════════════════════════════════════════"
echo "       NEXWAVE TRADING ENGINE - FULL RAW LOG STREAM"
echo "════════════════════════════════════════════════════════════════════"
echo ""

docker logs nexwave-trading-engine -f --tail 20
