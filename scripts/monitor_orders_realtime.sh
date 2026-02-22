#!/bin/bash
# Real-time order placement monitoring for Pacifica

echo "════════════════════════════════════════════════════════════════"
echo "  🔍 REAL-TIME ORDER PLACEMENT MONITORING - PACIFICA DEX"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check current status
echo "📊 Current Status:"
echo "────────────────────────────────────────────────────────────────"
docker logs nexwave-trading-engine 2>&1 | grep -E "Paper Trading|Pacifica client|Connected to Pacifica" | tail -3 | sed 's/\x1b\[[0-9;]*m//g'
echo ""

# Check for recent signals
echo "📈 Recent Signal Activity (last 5 minutes):"
echo "────────────────────────────────────────────────────────────────"
docker logs nexwave-trading-engine --since 5m 2>&1 | grep -E "BUY signal|SELL signal|Generated.*signal" | tail -5 | sed 's/\x1b\[[0-9;]*m//g' || echo "  No signals generated in last 5 minutes"
echo ""

# Check for recent orders
echo "✅ Recent Order Activity (last 5 minutes):"
echo "────────────────────────────────────────────────────────────────"
docker logs nexwave-trading-engine --since 5m 2>&1 | grep -E "Order placed|Placing.*Pacifica|✅ Order|TP/SL set" | tail -5 | sed 's/\x1b\[[0-9;]*m//g' || echo "  No orders placed in last 5 minutes"
echo ""

# Check for errors
echo "❌ Recent Errors (last 5 minutes):"
echo "────────────────────────────────────────────────────────────────"
docker logs nexwave-trading-engine --since 5m 2>&1 | grep -E "ERROR|Error|Failed.*Pacifica|Pacifica.*error" | tail -5 | sed 's/\x1b\[[0-9;]*m//g' || echo "  ✅ No errors detected"
echo ""

echo "════════════════════════════════════════════════════════════════"
echo "  📡 Starting real-time monitoring..."
echo "  Watching for: BUY/SELL signals → Order placement → TP/SL"
echo "  Press Ctrl+C to stop"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Real-time monitoring
docker logs nexwave-trading-engine -f 2>&1 | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    while IFS= read -r line; do
        timestamp=$(date '+%H:%M:%S')
        
        # BUY Signal
        if echo "$line" | grep -q "BUY signal"; then
            symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1)
            echo -e "${GREEN}[$timestamp] 🟢 BUY SIGNAL DETECTED: ${symbol}${NC}"
            echo "   $line"
            echo ""
        
        # SELL Signal
        elif echo "$line" | grep -q "SELL signal"; then
            symbol=$(echo "$line" | grep -oP 'for \K[A-Z0-9]+' | head -1)
            echo -e "${RED}[$timestamp] 🔴 SELL SIGNAL DETECTED: ${symbol}${NC}"
            echo "   $line"
            echo ""
        
        # Generated signal (order details)
        elif echo "$line" | grep -q "Generated.*signal"; then
            echo -e "${CYAN}[$timestamp] 📊 ORDER DETAILS:${NC}"
            echo "   $line"
            echo ""
        
        # Order placement on Pacifica
        elif echo "$line" | grep -qE "Placing.*order on Pacifica|Order placed.*pacifica_id"; then
            echo -e "${BLUE}[$timestamp] ✅ ORDER PLACED ON PACIFICA:${NC}"
            echo "   $line"
            echo ""
        
        # TP/SL set
        elif echo "$line" | grep -q "TP/SL set"; then
            symbol=$(echo "$line" | grep -oP 'TP/SL set: \K[A-Z0-9]+' | head -1)
            echo -e "${MAGENTA}[$timestamp] 🛡️  RISK PROTECTION SET: ${symbol}${NC}"
            echo "   $line"
            echo ""
        
        # Pacifica errors
        elif echo "$line" | grep -qE "Pacifica.*error|Pacifica.*Error|Failed.*Pacifica|Pacifica API error"; then
            echo -e "${RED}[$timestamp] ❌ PACIFICA ERROR:${NC}"
            echo "   $line"
            echo ""
        
        # Order errors
        elif echo "$line" | grep -qE "Error creating order|Order creation returned None|Failed to.*order"; then
            echo -e "${RED}[$timestamp] ❌ ORDER ERROR:${NC}"
            echo "   $line"
            echo ""
        
        # Paper trading mode (should not appear if paper_trading=False)
        elif echo "$line" | grep -q "PAPER TRADING"; then
            echo -e "${YELLOW}[$timestamp] ⚠️  PAPER MODE (not placing real orders):${NC}"
            echo "   $line"
            echo ""
        fi
    done

