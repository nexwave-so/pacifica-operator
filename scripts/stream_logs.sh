#!/bin/bash
# Nexwave Trading Engine Log Stream
# For livestream monitoring

clear
echo "======================================================================"
echo "           NEXWAVE TRADING ENGINE - LIVE MONITORING"
echo "======================================================================"
echo ""
echo "🤖 Autonomous Trading Agent | Volume-Weighted Momentum Strategy"
echo "💰 Portfolio: \$159 USDC (5x leverage = \$795-\$1,590 buying power)"
echo "📊 Monitoring: 30 trading pairs on Pacifica DEX"
echo "⚡ Signal Threshold: 0.1% momentum + 1.2x volume"
echo ""
echo "======================================================================"
echo ""

# Follow logs with nice filtering
docker logs nexwave-trading-engine -f 2>&1 | grep --line-buffered -E "(BUY signal|SELL signal|Order request sent|STOP LOSS|TAKE PROFIT|confidence|Generated|placed)" | while IFS= read -r line; do
    echo "[$(date '+%H:%M:%S')] $line"
done
