# Quick Start Guide

## Prerequisites

- Docker and Docker Compose installed
- Python 3.11+ (for local development)
- UV package manager (optional, for local development)

## Initial Setup

1. **Clone and navigate to the project:**
   ```bash
   cd nexwave
   ```

2. **Create environment file:**
   ```bash
   cp env.example .env
   ```

3. **Edit `.env` and configure:**
   - `POSTGRES_PASSWORD` - Set a secure password
   - `PACIFICA_WS_URL` - Pacifica WebSocket URL
   - `JWT_SECRET` - Generate a secure JWT secret
   - Other settings as needed

## Running with Docker Compose

1. **Start infrastructure services:**
   ```bash
   docker compose up -d --remove-orphans postgres redis zookeeper kafka
   ```

2. **Wait for services to be healthy (30-60 seconds)**

3. **Initialize database:**
   ```bash
   docker compose exec postgres psql -U nexwave -d nexwave -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
   ```

4. **Create database tables:**
   ```bash
   # You'll need to run Alembic migrations or create tables manually
   # For now, you can use SQLAlchemy to create tables:
   docker compose run --rm api-gateway python -c "from nexwave.db.session import engine; from nexwave.db.models import Base; import asyncio; asyncio.run(Base.metadata.create_all(engine))"
   ```

5. **Start all services:**
   ```bash
   docker compose up -d --remove-orphans
   ```

6. **Check service status:**
   ```bash
   docker compose ps
   ```

7. **View logs:**
   ```bash
   docker compose logs -f [service-name]
   ```

## Local Development Setup

1. **Install UV (if not already installed):**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

4. **Set up environment variables:**
   ```bash
   export DATABASE_URL="postgresql://nexwave:nexwave@localhost:5432/nexwave"
   export REDIS_URL="redis://localhost:6379"
   export LOG_LEVEL="INFO"
   ```

5. **Run services individually:**
   ```bash
   # Terminal 1: Market Data Service
   python -m src.nexwave.services.market_data.client

   # Terminal 2: Database Writer Service
   python -m src.nexwave.services.db_writer.service

   # Terminal 3: API Gateway
   python -m src.nexwave.services.api_gateway.main
   ```

## Testing the API

Once the API Gateway is running, you can test it:

```bash
# Health check
curl http://localhost:8000/health

# Get latest prices
curl http://localhost:8000/api/v1/latest-prices

# Get ticks for BTC
curl "http://localhost:8000/api/v1/ticks/BTC?limit=10"

# Get candles for BTC (1h timeframe)
curl "http://localhost:8000/api/v1/candles/BTC/1h?limit=10"

# Get whale activities
curl "http://localhost:8000/api/v1/whales?limit=10"
```

## API Documentation

Once the API Gateway is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running: `docker compose ps postgres`
- Check database URL in `.env`
- Verify password matches in `.env` and docker-compose.yml

### Redis Connection Issues
- Ensure Redis is running: `docker compose ps redis`
- Check Redis URL in `.env`
- Test connection: `docker compose exec redis redis-cli ping`

### WebSocket Connection Issues
- Check Pacifica WebSocket URL is correct
- Verify network connectivity
- Check logs: `docker compose logs market-data`

### Service Won't Start
- Check logs: `docker compose logs [service-name]`
- Verify all environment variables are set
- Ensure dependencies are installed (check Dockerfile)

## Next Steps

1. Set up Alembic for database migrations
2. Implement Whale Tracker Service
3. Implement Trading Engine Service
4. Implement Order Management Service
5. Set up TimescaleDB continuous aggregates for candles
6. Add monitoring with Prometheus and Grafana

See `PROJECT_STATUS.md` for detailed implementation status.

