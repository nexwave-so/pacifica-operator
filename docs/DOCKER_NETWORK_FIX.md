# Docker Network Configuration Fix

**Date:** November 3, 2025
**Issue:** Backend services unable to connect to Redis/Postgres - DNS resolution failures
**Status:** ✅ Resolved

## Problem Description

After deploying the application, the backend services (API gateway, market-data, db-writer, whale-tracker) were experiencing DNS resolution failures when trying to connect to Redis and Postgres:

```
Error -3 connecting to redis:6379. Temporary failure in name resolution.
```

### Root Cause

The Docker Compose configuration had a network segmentation issue:
- Backend services were configured to use `nexwave-network`
- Infrastructure services (Redis, Postgres, Zookeeper, Kafka) had no explicit network configuration
- Docker automatically placed them on `nexwave_default` network
- Services on different networks cannot resolve each other's hostnames via Docker DNS

## Solution

Updated `docker compose.yml` to explicitly add all infrastructure services to the `nexwave-network`:

### Changes Made

**Modified Services:**
1. `postgres` - Added `networks: - nexwave-network`
2. `redis` - Added `networks: - nexwave-network`
3. `zookeeper` - Added `networks: - nexwave-network`
4. `kafka` - Added `networks: - nexwave-network`

### Code Changes

```yaml
# Before (postgres example)
postgres:
  image: timescale/timescaledb-ha:pg15
  container_name: nexwave-postgres
  # ... other config
  # No network specified - defaults to nexwave_default

# After
postgres:
  image: timescale/timescaledb-ha:pg15
  container_name: nexwave-postgres
  # ... other config
  networks:
    - nexwave-network
```

## Database Initialization

Created `scripts/init_db.py` to initialize the database schema. This script:
- Creates all SQLAlchemy models (ticks, whale_activities, orders, positions, pairs)
- Converts the `ticks` table to a TimescaleDB hypertable
- Ensures proper indexes are created

### Usage

```bash
# Run from within the API container
docker exec nexwave-api python -c "
import asyncio
from sqlalchemy import text
from nexwave.db.session import engine, Base
from nexwave.db import models

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text(\"SELECT create_hypertable('ticks', 'time', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)\"))

asyncio.run(init_db())
"
```

## Deployment Steps

When deploying or restarting the application:

1. **Stop all services:**
   ```bash
   docker compose down
   ```

2. **Start services with new configuration:**
   ```bash
   docker compose up -d
   ```

3. **Initialize database (if needed):**
   ```bash
   # Check if tables exist
   docker exec nexwave-postgres psql -U nexwave -d nexwave -c "\dt"

   # If no tables, run initialization
   docker exec nexwave-api python scripts/init_db.py
   ```

4. **Verify services are healthy:**
   ```bash
   docker ps
   # All services should show "Up X seconds (healthy)" or "Up X seconds"
   ```

5. **Check API endpoints:**
   ```bash
   curl -sk https://localhost/api/v1/pairs | head -100
   curl -sk https://localhost/api/v1/latest-prices
   ```

## Verification

### Service Health Checks

```bash
# Check all containers are running
docker ps

# Check API logs for Redis connection
docker logs nexwave-api | grep -i redis
# Should see: "Connected to Redis"

# Check market data service
docker logs nexwave-market-data | grep -i "connected\|subscribed"
# Should see: "WebSocket connected successfully" and "Subscribed to 120 channels"

# Check database tables
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "\dt"
# Should show: ticks, pairs, whale_activities, orders, positions
```

### Network Inspection

```bash
# List networks
docker network ls

# Inspect nexwave network
docker network inspect nexwave_nexwave-network

# Verify all services are on the same network
docker inspect nexwave-api | grep -A 10 "Networks"
docker inspect nexwave-redis | grep -A 10 "Networks"
```

## Troubleshooting

### DNS Still Failing?

1. Ensure `docker compose.yml` has networks defined for all services
2. Restart Docker daemon: `sudo systemctl restart docker`
3. Recreate networks: `docker compose down && docker network prune -f && docker compose up -d`

### Services Not Starting?

1. Check logs: `docker logs <container-name>`
2. Verify environment variables: `docker exec <container> printenv | grep DATABASE_URL`
3. Check disk space: `df -h`

### Database Tables Missing?

1. Run init script manually (see Database Initialization above)
2. Check PostgreSQL logs: `docker logs nexwave-postgres`
3. Verify TimescaleDB extension: `docker exec nexwave-postgres psql -U nexwave -d nexwave -c "\dx"`

## Impact

### Before Fix
- ❌ All backend services failing with DNS errors
- ❌ No data being collected or stored
- ❌ Dashboard showing no data
- ❌ API returning 500 errors

### After Fix
- ✅ All services connecting successfully
- ✅ Market data service subscribed to 120 channels
- ✅ Database initialized with proper schema
- ✅ API endpoints responding correctly
- ✅ Dashboard loading (waiting for market data)

## Related Files

- `docker compose.yml` - Main configuration file (lines 4-244)
- `scripts/init_db.py` - Database initialization script
- `src/nexwave/db/models.py` - SQLAlchemy models
- `src/nexwave/db/session.py` - Database session configuration

## Lessons Learned

1. **Always explicitly define networks** in Docker Compose when using custom networks
2. **Use Docker Compose health checks** to catch connection issues early
3. **Separate infrastructure initialization** (database schema) from application startup
4. **Document network topology** to prevent similar issues

## References

- Docker Networking: https://docs.docker.com/network/
- Docker Compose Networks: https://docs.docker.com/compose/networking/
- TimescaleDB Setup: https://docs.timescale.com/self-hosted/latest/install/
