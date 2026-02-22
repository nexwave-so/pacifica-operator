# Nexwave Trading Engine - Troubleshooting Guide

## Quick Diagnosis Checklist

When troubleshooting data flow issues, follow this systematic approach:

### 1. Check Service Health

```bash
docker compose ps
```

**Expected**: All services should be "Up" (some may show "unhealthy" initially but still function)

### 2. Verify Pacifica Connection

```bash
docker logs nexwave-market-data --tail 50
```

**Look for**:
- ✅ "WebSocket connected successfully"
- ✅ "Subscribed to X data sources"
- ❌ Authentication errors
- ❌ Connection refused

### 3. Check Data Flow

```bash
# Check if tick data is arriving
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT symbol, COUNT(*) as tick_count, MAX(time) as latest_tick
  FROM ticks
  WHERE symbol IN ('BTC', 'ETH', 'SOL', 'BNB')
  GROUP BY symbol;
"
```

**Expected**: Increasing tick counts, recent timestamps

### 4. Verify Candle Aggregation

```bash
# Check 15-minute candles (used by VWM strategy)
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT symbol, COUNT(*) as candle_count,
         MIN(bucket) as earliest, MAX(bucket) as latest
  FROM candles_15m
  WHERE symbol IN ('BTC', 'ETH', 'SOL', 'BNB')
  GROUP BY symbol;
"
```

**Required**: 20 candles minimum for trading (5 hours of data)

### 5. Check Trading Engine

```bash
docker logs nexwave-trading-engine --tail 100 | grep -i "error\|warning"
```

**Common issues**:
- "Not enough candle data" → Wait for data accumulation
- "Keypair not initialized" → Missing PACIFICA_AGENT_WALLET_PRIVKEY

---

## Common Issues & Solutions

### Issue 1: "Not enough candle data" Warnings

**Symptoms**:
```
WARNING | Not enough candle data for BTC
WARNING | Not enough candle data for ETH
```

**Root Cause**: Trading strategies require historical data (default: 20 candles × 15 minutes = 5 hours)

**Solution**:
1. **Fresh System**: Wait for data accumulation
   - 15 min: 1 candle (minimal trading)
   - 1 hour: 4 candles (basic signals)
   - 5 hours: 20 candles (full operation)

2. **Manually Refresh Aggregates** (if data exists but candles aren't updating):
   ```bash
   docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
     CALL refresh_continuous_aggregate('candles_1m', NULL, NULL);
     CALL refresh_continuous_aggregate('candles_5m', NULL, NULL);
     CALL refresh_continuous_aggregate('candles_15m', NULL, NULL);
   "
   ```

3. **Check Data Age**:
   ```bash
   docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
     SELECT NOW() - MIN(time) AS oldest_data_age FROM ticks;
   "
   ```

**Prevention**: Keep the system running continuously to maintain historical data

---

### Issue 2: "Keypair not initialized" / Position Sync Errors

**Symptoms**:
```
ERROR | Error syncing positions from Pacifica: Keypair not initialized
WARNING | Pacifica private key not properly configured
```

**Root Cause**: Missing or invalid Solana wallet private key in `.env`

**Solution**:
1. Edit `.env` file:
   ```bash
   PACIFICA_AGENT_WALLET_PRIVKEY=your_actual_solana_private_key_here
   ```

2. Restart affected services:
   ```bash
   docker compose restart trading-engine order-management
   ```

3. Verify fix:
   ```bash
   docker logs nexwave-trading-engine --tail 20 | grep -i keypair
   # Should not show errors
   ```

**Security Note**: Never commit actual private keys to git. Use placeholder values in version control.

---

### Issue 3: Foreign Key Violations for Unknown Symbols

**Symptoms**:
```
ERROR | insert or update on table "_hyper_1_1_chunk" violates foreign key constraint
DETAIL: Key (symbol)=(NEAR) is not present in table "pairs".
```

**Root Cause**: Pacifica sends data for symbols not configured in your `pairs` table

**Impact**: Low - Only affects unconfigured symbols, doesn't impact primary trading pairs

**Solution** (if you want to trade these symbols):
1. Check available symbols from Pacifica:
   ```bash
   docker logs nexwave-db-writer --tail 200 | grep "foreign key" | grep -oP "(?<=\(symbol\)=\()[A-Z0-9]+(?=\))" | sort -u
   ```

2. Add missing symbols to database:
   ```sql
   INSERT INTO pairs (symbol, category, whale_threshold_usd, leverage)
   VALUES ('NEAR', 'emerging', 5000, 5);
   ```

**Alternative**: Ignore - System will continue working for configured pairs

---

### Issue 4: WebSocket Connection Failures

**Symptoms**:
```
ERROR | WebSocket connection failed
ERROR | Failed to connect to wss://ws.pacifica.fi/ws
```

**Common Causes**:
1. **Wrong header parameter**: Recent fix changed `extra_headers` to `additional_headers`
2. **Invalid API key**: Check `PACIFICA_API_KEY` in `.env`
3. **Network issues**: Verify external connectivity

**Solution**:
1. Verify API credentials:
   ```bash
   grep PACIFICA .env
   ```

2. Test connection manually:
   ```bash
   docker exec nexwave-market-data python -c "
   import asyncio
   import websockets
   import os

   async def test():
       uri = os.getenv('PACIFICA_WS_URL', 'wss://ws.pacifica.fi/ws')
       async with websockets.connect(uri) as ws:
           print('Connected successfully')

   asyncio.run(test())
   "
   ```

3. Check recent code changes:
   ```bash
   git log --oneline -10 src/nexwave/services/market_data/client.py
   ```

---

### Issue 5: Continuous Aggregates Not Updating

**Symptoms**:
- Tick data exists but candles are stale
- `MAX(bucket)` timestamp is old despite recent ticks

**Root Cause**: TimescaleDB refresh policies may be behind schedule

**Solution**:
1. Check refresh policy status:
   ```sql
   SELECT view_name, schedule_interval,
          config->>'start_offset' as start_offset,
          config->>'end_offset' as end_offset
   FROM timescaledb_information.jobs j
   JOIN timescaledb_information.continuous_aggregates ca
     ON j.hypertable_name = ca.materialization_hypertable_name
   WHERE view_name LIKE 'candles_%';
   ```

2. Manual refresh (immediate):
   ```bash
   docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
     CALL refresh_continuous_aggregate('candles_1m', NULL, NULL);
     CALL refresh_continuous_aggregate('candles_5m', NULL, NULL);
     CALL refresh_continuous_aggregate('candles_15m', NULL, NULL);
     CALL refresh_continuous_aggregate('candles_1h', NULL, NULL);
   "
   ```

3. Verify refresh:
   ```bash
   docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
     SELECT view_name,
            (SELECT MAX(bucket) FROM public.candles_1m) as max_bucket,
            NOW() as current_time
     FROM timescaledb_information.continuous_aggregates
     WHERE view_name = 'candles_1m';
   "
   ```

---

### Issue 6: Redis Authentication Errors

**Symptoms**:
```
ERROR | NOAUTH Authentication required
ERROR | Connection refused - redis:6379
```

**Root Cause**: Redis password not configured or mismatched

**Solution**:
1. Check Redis configuration in `docker-compose.yml`:
   ```yaml
   redis:
     command: redis-server --requirepass ${REDIS_PASSWORD:-nexwave123}
   ```

2. Verify `.env` has Redis password:
   ```bash
   grep REDIS .env
   ```

3. Ensure services use correct Redis URL:
   ```bash
   # Should be: redis://:password@redis:6379
   # NOT: redis://redis:6379
   ```

4. Update `src/nexwave/common/config.py` if needed:
   ```python
   redis_password: str = "nexwave123"  # Must match docker-compose
   ```

5. Restart services:
   ```bash
   docker compose restart redis market-data db-writer
   ```

---

## Diagnostic Commands Reference

### System Health

```bash
# Service status
docker compose ps

# Resource usage
docker stats --no-stream

# Recent logs from all services
docker compose logs --tail=50 --timestamps

# Follow logs in real-time
docker compose logs -f trading-engine
```

### Database Queries

```bash
# Total tick count by symbol
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT symbol, COUNT(*) as count
  FROM ticks
  GROUP BY symbol
  ORDER BY count DESC;
"

# Data age and volume
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT
    NOW() - MIN(time) AS data_age,
    NOW() - MAX(time) AS last_update_ago,
    COUNT(*) as total_ticks
  FROM ticks;
"

# Candle availability
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT
    '1m' as timeframe, COUNT(*) as candles FROM candles_1m
  UNION ALL
  SELECT '5m', COUNT(*) FROM candles_5m
  UNION ALL
  SELECT '15m', COUNT(*) FROM candles_15m
  UNION ALL
  SELECT '1h', COUNT(*) FROM candles_1h;
"

# Check continuous aggregate health
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT * FROM timescaledb_information.continuous_aggregates;
"
```

### Service-Specific

```bash
# Market data - WebSocket status
docker logs nexwave-market-data --tail 100 | grep -i "websocket\|connected\|subscribed"

# DB writer - Write performance
docker logs nexwave-db-writer --tail 100 | grep -i "wrote\|error"

# Trading engine - Signal generation
docker logs nexwave-trading-engine --tail 100 | grep -i "signal\|position\|trade"

# Order management - Order status
docker logs nexwave-order-management --tail 50 | grep -i "order\|filled\|rejected"
```

---

## Monitoring Best Practices

### 1. Data Pipeline Health Check Script

Create `scripts/health_check.sh`:

```bash
#!/bin/bash
set -e

echo "=== Nexwave Health Check ==="
echo ""

# Service status
echo "1. Service Status:"
docker compose ps | grep -E "nexwave-(market-data|db-writer|trading-engine)"
echo ""

# Data freshness
echo "2. Data Freshness:"
docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
  SELECT
    'Last tick: ' || (NOW() - MAX(time))::text as freshness
  FROM ticks;
"

# Candle counts
echo "3. Candle Availability:"
docker exec nexwave-postgres psql -U nexwave -d nexwave -t -c "
  SELECT
    timeframe,
    candles,
    CASE
      WHEN candles >= 20 THEN 'Ready'
      ELSE 'Accumulating (' || ROUND(candles::numeric/20*100) || '%)'
    END as status
  FROM (
    SELECT '15m' as timeframe, COUNT(*) as candles
    FROM candles_15m WHERE symbol = 'BTC'
  ) sub;
"

echo ""
echo "=== End Health Check ==="
```

### 2. Continuous Monitoring

Set up automated checks:

```bash
# Run health check every 5 minutes
*/5 * * * * /var/www/nexwave/scripts/health_check.sh >> /var/log/nexwave_health.log 2>&1
```

### 3. Alert Thresholds

- **Data Lag** > 5 minutes: Investigate market-data service
- **Candle Lag** > 15 minutes: Manually refresh aggregates
- **Error Rate** > 10 errors/min: Check service logs
- **Disk Usage** > 80%: Consider data retention policies

---

## Recovery Procedures

### Full System Restart

```bash
# Stop all services
docker compose down

# Clear any stuck containers
docker system prune -f

# Restart (preserves database)
docker compose up -d --remove-orphans

# Verify startup
docker compose logs -f
```

### Database Reset (CAUTION: Deletes all data)

```bash
# Stop services
docker compose down

# Remove volumes
docker volume rm nexwave_postgres_data

# Reinitialize
docker compose up -d postgres
sleep 10

# Run migrations
for migration in migrations/*.sql; do
  docker exec -i nexwave-postgres psql -U nexwave -d nexwave < "$migration"
done

# Start remaining services
docker compose up -d
```

### Service-Specific Restart

```bash
# Rebuild and restart single service
docker compose up -d --build --no-deps --remove-orphans trading-engine

# Check logs
docker logs -f nexwave-trading-engine
```

---

## Environment Configuration Checklist

Essential `.env` variables for data flow:

```bash
# Required for market data
✅ PACIFICA_API_KEY=<your_api_key>
✅ PACIFICA_WS_URL=wss://ws.pacifica.fi/ws
✅ PACIFICA_API_URL=https://api.pacifica.fi/api/v1

# Required for trading (can use placeholder for read-only mode)
⚠️  PACIFICA_AGENT_WALLET_PRIVKEY=<your_private_key>
⚠️  PACIFICA_AGENT_WALLET_PUBKEY=<your_public_key>

# Database
✅ DATABASE_URL=postgresql://nexwave:${POSTGRES_PASSWORD}@postgres:5432/nexwave
✅ POSTGRES_PASSWORD=<secure_password>

# Redis
✅ REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
⚠️  REDIS_PASSWORD=nexwave123  # Must match docker-compose.yml

# Trading configuration
✅ STRATEGY=volume_weighted_momentum
✅ VWM_LOOKBACK_PERIOD=20
✅ VWM_TIMEFRAME=15m  # Default in config.py

# Symbols to trade
✅ SYMBOLS=BTC,ETH,BNB,SOL,ZEC
```

---

## Contact & Resources

- **Documentation**: `/var/www/nexwave/README.md`
- **API Docs**: `http://localhost:8000/docs`
- **Project Docs**: `/var/www/nexwave/docs/`
- **GitHub Issues**: Report bugs or questions

---

**Last Updated**: 2025-12-06
**Version**: 1.0.0
**Author**: AI Engineering Team
