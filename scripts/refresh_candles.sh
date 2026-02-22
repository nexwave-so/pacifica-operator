#!/bin/bash
# Refresh candles materialized view every 15 minutes
# This script should be run via cron or as a background task

while true; do
    echo "[$(date)] Refreshing candles_15m_ohlcv materialized view..."
    docker exec nexwave-postgres psql -U nexwave -d nexwave -c "REFRESH MATERIALIZED VIEW candles_15m_ohlcv;" > /dev/null 2>&1

    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ Candles refreshed successfully"
    else
        echo "[$(date)] ❌ Failed to refresh candles"
    fi

    # Sleep for 15 minutes (900 seconds)
    sleep 900
done
