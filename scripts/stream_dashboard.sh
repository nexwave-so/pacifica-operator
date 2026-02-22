#!/bin/bash
# Nexwave Multi-Service Dashboard
# Shows Trading Engine + Market Data + API activity

clear

# Function to display header
show_header() {
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║          NEXWAVE AUTONOMOUS TRADING AGENT - LIVE DASHBOARD         ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""
    echo "📊 Strategy: Volume-Weighted Momentum (VWM)"
    echo "💰 Portfolio: \$159 USDC → \$795-\$1,590 (with 5x leverage)"
    echo "🎯 Pairs: 30 perpetuals on Pacifica DEX"
    echo "⚡ Demo Mode: 0.1% threshold, 15 candle lookback"
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    echo ""
}

show_header

# Follow trading engine logs
docker logs nexwave-trading-engine -f --tail 0 2>&1 | grep --line-buffered -E "(signal|Order|confidence|STOP|PROFIT)" | while IFS= read -r line; do
    timestamp=$(date '+%H:%M:%S')
    
    # Highlight important events
    if echo "$line" | grep -q "BUY signal"; then
        echo "[$timestamp] 🟢 $line"
    elif echo "$line" | grep -q "SELL signal"; then
        echo "[$timestamp] 🔴 $line"
    elif echo "$line" | grep -q "Order request sent"; then
        echo "[$timestamp] ✅ $line"
    elif echo "$line" | grep -q "STOP LOSS"; then
        echo "[$timestamp] 🛑 $line"
    elif echo "$line" | grep -q "TAKE PROFIT"; then
        echo "[$timestamp] 💰 $line"
    else
        echo "[$timestamp] $line"
    fi
done
