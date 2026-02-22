#!/bin/bash
# Live Trading Engine Monitoring Dashboard
# Shows real-time signal generation, positions, and orders

clear

echo "════════════════════════════════════════════════════════════════════════════════"
echo "                    NEXWAVE TRADING ENGINE - LIVE MONITOR                       "
echo "════════════════════════════════════════════════════════════════════════════════"
echo "Timestamp: $(date -u '+%Y-%m-%d %H:%M:%S') UTC"
echo ""

# 1. Docker Container Status
echo "📦 CONTAINER STATUS"
echo "────────────────────────────────────────────────────────────────────────────────"
docker ps --filter "name=nexwave" --format "table {{.Names}}\t{{.Status}}" | grep -E "nexwave-(trading-engine|order-management|market-data)"
echo ""

# 2. Market Data Freshness
echo "📊 MARKET DATA STATUS"
echo "────────────────────────────────────────────────────────────────────────────────"
docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
SELECT 
    COUNT(DISTINCT symbol) as active_markets,
    COUNT(CASE WHEN age_seconds < 300 THEN 1 END) as fresh_data,
    ROUND(AVG(age_seconds)::numeric, 1) as avg_age_sec
FROM (
    SELECT DISTINCT ON (symbol) 
        symbol, 
        EXTRACT(EPOCH FROM (NOW() - time)) as age_seconds
    FROM ticks 
    ORDER BY symbol, time DESC
) t;
" | awk '{print "Active Markets: " $1 " | Fresh Data (< 5min): " $2 "/" $1 " | Avg Age: " $3 "s"}'

echo ""
echo "Recent Price Updates (last 5):"
docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
SELECT 
    symbol || ' | $' || ROUND(price::numeric, 4) || ' | ' || 
    CASE 
        WHEN age_sec < 60 THEN age_sec || 's ago'
        ELSE ROUND(age_sec/60) || 'm ago'
    END as info
FROM (
    SELECT DISTINCT ON (symbol) 
        symbol, 
        price,
        EXTRACT(EPOCH FROM (NOW() - time))::int as age_sec
    FROM ticks 
    ORDER BY symbol, time DESC
    LIMIT 5
) t;
" | awk '{printf "  %s\n", $0}'

echo ""

# 3. Open Positions
echo "💼 OPEN POSITIONS"
echo "────────────────────────────────────────────────────────────────────────────────"
POSITION_COUNT=$(docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "SELECT COUNT(*) FROM positions;")

if [ "$POSITION_COUNT" -gt 0 ]; then
    echo "Total Positions: $POSITION_COUNT"
    echo ""
    docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
    SELECT 
        CASE 
            WHEN unrealized_pnl >= 0 THEN '🟢 ' || symbol
            ELSE '🔴 ' || symbol
        END || ' | ' || 
        LPAD(side, 5) || ' | ' ||
        'Amount: ' || ROUND(amount::numeric, 4) || ' | ' ||
        'Entry: $' || ROUND(entry_price::numeric, 2) || ' | ' ||
        'Current: $' || ROUND(current_price::numeric, 2) || ' | ' ||
        'PnL: $' || ROUND(unrealized_pnl::numeric, 2)
    FROM positions
    ORDER BY opened_at DESC;
    " | awk '{printf "  %s\n", $0}'
    
    # Total P&L
    TOTAL_PNL=$(docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "SELECT ROUND(SUM(unrealized_pnl)::numeric, 2) FROM positions;")
    echo ""
    if (( $(echo "$TOTAL_PNL >= 0" | bc -l) )); then
        echo "  📈 Total Unrealized P&L: \$$TOTAL_PNL"
    else
        echo "  📉 Total Unrealized P&L: \$$TOTAL_PNL"
    fi
else
    echo "No open positions"
fi

echo ""

# 4. Recent Orders (Last 24h)
echo "📝 RECENT ORDERS (Last 24 hours)"
echo "────────────────────────────────────────────────────────────────────────────────"
ORDER_COUNT=$(docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "SELECT COUNT(*) FROM orders WHERE created_at > NOW() - INTERVAL '24 hours';")

if [ "$ORDER_COUNT" -gt 0 ]; then
    echo "Total Orders (24h): $ORDER_COUNT"
    echo ""
    docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
    SELECT 
        CASE status
            WHEN 'submitted' THEN '🟡'
            WHEN 'filled' THEN '✅'
            WHEN 'partial' THEN '🟠'
            WHEN 'cancelled' THEN '⛔'
            WHEN 'failed' THEN '❌'
            ELSE '❓'
        END || ' [' || TO_CHAR(created_at, 'HH24:MI:SS') || '] ' ||
        RPAD(symbol, 8) || ' | ' ||
        RPAD(side, 4) || ' | ' ||
        ROUND(amount::numeric, 4) || ' @ $' || ROUND(price::numeric, 2) || ' | ' ||
        'Status: ' || status
    FROM orders
    WHERE created_at > NOW() - INTERVAL '24 hours'
    ORDER BY created_at DESC
    LIMIT 10;
    " | awk '{printf "  %s\n", $0}'
else
    echo "No orders in last 24 hours"
fi

echo ""

# 5. Signal Generation Activity
echo "⚡ SIGNAL GENERATION (Last 30 seconds)"
echo "────────────────────────────────────────────────────────────────────────────────"
docker logs nexwave-trading-engine --since 30s 2>&1 | grep -E "(Signal Check|BUY signal|SELL signal|TAKE PROFIT|STOP LOSS|Generated)" | tail -10 | sed 's/\x1b\[[0-9;]*m//g' | cut -d'|' -f4- | sed 's/^[ \t]*/  /'

echo ""

# 6. Strategy Info
echo "📊 STRATEGY CONFIGURATION"
echo "────────────────────────────────────────────────────────────────────────────────"
echo "  Strategy: Volume Weighted Momentum (VWM)"
echo "  Scan Interval: 60 seconds"
echo "  Active Symbols: 30 pairs"
echo "  Entry Threshold: VWM > 0.001 + Volume > 1.2x avg"
echo "  Exit Threshold: VWM < -0.001 or Stop Loss/Take Profit"
echo "  Position Sizing: 5% - 10% with up to 5x leverage"

echo ""

# 7. System Health
echo "🏥 SYSTEM HEALTH"
echo "────────────────────────────────────────────────────────────────────────────────"

# Check market data age
DATA_AGE=$(docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
SELECT EXTRACT(EPOCH FROM (NOW() - MAX(time)))::int FROM ticks;
")

if [ "$DATA_AGE" -lt 60 ]; then
    echo "  ✅ Market data stream: HEALTHY (${DATA_AGE}s old)"
elif [ "$DATA_AGE" -lt 300 ]; then
    echo "  ⚠️  Market data stream: DELAYED (${DATA_AGE}s old)"
else
    echo "  ❌ Market data stream: STALE ($((DATA_AGE/60))m old)"
fi

# Check if trading engine is running
if docker ps | grep -q "nexwave-trading-engine.*healthy"; then
    echo "  ✅ Trading engine: RUNNING & HEALTHY"
elif docker ps | grep -q "nexwave-trading-engine"; then
    echo "  ⚠️  Trading engine: RUNNING (waiting for health check)"
else
    echo "  ❌ Trading engine: NOT RUNNING"
fi

# Check order management
if docker ps | grep -q "nexwave-order-management.*healthy"; then
    echo "  ✅ Order management: RUNNING & HEALTHY"
elif docker ps | grep -q "nexwave-order-management"; then
    echo "  ⚠️  Order management: RUNNING (waiting for health check)"
else
    echo "  ❌ Order management: NOT RUNNING"
fi

echo "  ✅ Database: CONNECTED"

echo ""
echo "════════════════════════════════════════════════════════════════════════════════"
echo ""
echo "💡 TIP: Run 'watch -n 5 /var/www/nexwave/monitor_live.sh' for auto-refresh"
echo "📊 Dashboard: https://nexwave.so/dashboard"
echo "📝 Logs: docker logs -f nexwave-trading-engine"
echo ""

