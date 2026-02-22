#!/bin/bash
# High-Momentum Strategy Monitoring Script
# Run this every hour or after key events to track performance

echo "======================================"
echo "HIGH-MOMENTUM STRATEGY MONITOR"
echo "Date: $(date)"
echo "======================================"
echo ""

# 1. Current Positions
echo "📊 CURRENT POSITIONS:"
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
SELECT
    symbol,
    side,
    amount,
    entry_price,
    current_price,
    ROUND((unrealized_pnl)::numeric, 2) as pnl,
    ROUND((unrealized_pnl / (amount * entry_price) * 100)::numeric, 2) as roi_pct,
    ROUND(EXTRACT(EPOCH FROM (NOW() - opened_at))/3600::numeric, 1) as hours_open
FROM positions
ORDER BY opened_at DESC;
" 2>&1
echo ""

# 2. Recent Signals (last 24 hours)
echo "🔍 SIGNALS GENERATED (Last Hour):"
docker logs --since 1h nexwave-trading-engine 2>&1 | \
    grep -E "(BUY signal|SELL signal|Generated.*signal)" | \
    tail -10
echo ""

# 3. High-Momentum Candidates (VWM > 0.003)
echo "🚀 HIGH-MOMENTUM PAIRS (VWM > 0.3%):"
docker logs --tail 200 nexwave-trading-engine 2>&1 | \
    grep "Signal Check" | \
    awk -F'VWM=' '{print $2}' | \
    awk -F' ' '{if ($1 > 0.003 || $1 < -0.003) print $0}' | \
    tail -10
echo ""

# 4. Trading Statistics (last 24 hours)
echo "📈 TRADING STATISTICS (24H):"
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
SELECT
    COUNT(*) as total_trades,
    COUNT(DISTINCT symbol) as unique_symbols,
    SUM(CASE WHEN side = 'bid' THEN 1 ELSE 0 END) as longs,
    SUM(CASE WHEN side = 'ask' THEN 1 ELSE 0 END) as shorts,
    ROUND(AVG(amount * price)::numeric, 2) as avg_position_usd
FROM orders
WHERE created_at > NOW() - INTERVAL '24 hours';
" 2>&1
echo ""

# 5. Capital Utilization
echo "💰 CAPITAL UTILIZATION:"
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
SELECT
    COUNT(*) as open_positions,
    ROUND(SUM(amount * current_price)::numeric, 2) as capital_deployed,
    ROUND((SUM(amount * current_price) / 435.0 * 100)::numeric, 1) as utilization_pct,
    ROUND(SUM(unrealized_pnl)::numeric, 2) as total_unrealized_pnl
FROM positions;
" 2>&1
echo ""

# 6. Recent Errors/Warnings
echo "⚠️  RECENT WARNINGS (Last Hour):"
docker logs --since 1h nexwave-trading-engine 2>&1 | \
    grep -E "(WARNING|ERROR)" | \
    tail -5
echo ""

# 7. Strategy Parameters
echo "⚙️  ACTIVE STRATEGY PARAMETERS:"
grep "VWM_" /var/www/nexwave/.env | grep -v "^#"
echo ""

echo "======================================"
echo "Monitor complete. Re-run to refresh."
echo "======================================"
