#!/bin/bash
# Real-time monitoring script for order placement on Pacifica

echo "🔍 Monitoring Trading Engine for Order Placement on Pacifica"
echo "============================================================"
echo ""
echo "Watching for:"
echo "  ✅ Signal generation (BUY/SELL)"
echo "  ✅ Order placement attempts"
echo "  ✅ Pacifica API calls"
echo "  ✅ TP/SL setting"
echo "  ❌ Any errors"
echo ""
echo "Press Ctrl+C to stop"
echo ""
echo "============================================================"
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Monitor logs with filtering
docker logs nexwave-trading-engine -f 2>&1 | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    while IFS= read -r line; do
        # Signal generation
        if echo "$line" | grep -qE "BUY signal|SELL signal"; then
            echo -e "${GREEN}📊 SIGNAL:${NC} $line"
        
        # Order placement
        elif echo "$line" | grep -qE "Order placed|Order created|Placing.*order on Pacifica"; then
            echo -e "${CYAN}✅ ORDER:${NC} $line"
        
        # Pacifica API calls
        elif echo "$line" | grep -qE "Pacifica|pacifica_id|TP/SL set"; then
            echo -e "${BLUE}🌐 PACIFICA:${NC} $line"
        
        # Errors
        elif echo "$line" | grep -qE "ERROR|Error|Failed|failed"; then
            echo -e "${RED}❌ ERROR:${NC} $line"
        
        # Warnings
        elif echo "$line" | grep -qE "WARNING|Warning|⚠️"; then
            echo -e "${YELLOW}⚠️  WARNING:${NC} $line"
        
        # Generated signal (order details)
        elif echo "$line" | grep -qE "Generated.*signal|confidence="; then
            echo -e "${GREEN}📈 SIGNAL DETAILS:${NC} $line"
        
        # Paper trading mode
        elif echo "$line" | grep -qE "PAPER TRADING|paper_trading"; then
            echo -e "${YELLOW}📝 PAPER MODE:${NC} $line"
        fi
    done

