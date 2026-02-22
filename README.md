# Nexwave: Autonomous Trading Agent for Solana

Nexwave is an autonomous trading agent built for Pacifica perpetual DEX on Solana. **Pacifica Operator is the dominant scalper strategy** (5m, tight SL/TP, volume confirmation); real-time market data and algorithmic trading, operated by an [OpenClaw](https://github.com/openclaw/openclaw) agent (e.g., Nexbot).

> **Note on Agent Naming**: Throughout this documentation, "Nexbot" refers to our specific instance of an OpenClaw agent. If you are deploying your own agent using OpenClaw, please replace "Nexbot" with your chosen agent name in your configurations and documentation.

## Features

- **30 Trading Pairs**: Full Pacifica perpetual markets (BTC, ETH, SOL, DOGE, LINK, and 25+ more)
- **5 Trading Strategies**: Momentum and mean reversion strategies with risk management
- **Real-time Market Data**: <50ms API latency, TimescaleDB time-series optimization
- **Automated Risk Management**: Symbol blacklist, trade frequency limits, position sizing
- **REST & WebSocket APIs**: FastAPI backend with comprehensive endpoints

## 📊 Trading Pairs (30 Total)

| Category | Count | Examples |
|----------|-------|----------|
| **Major** | 3 | BTC, ETH, SOL |
| **Mid-Cap** | 7 | HYPE, XRP, AAVE, BNB, ZEC |
| **Emerging** | 14 | DOGE, LINK, SUI, TAO, AVAX, UNI |
| **Small-Cap** | 6 | PENGU, LDO, CRV, 2Z, MON |

## Architecture

Lean microservices architecture optimized for real-time trading:

```
Pacifica DEX (WebSocket/REST)
  ↓
Market Data Service → Redis Pub/Sub
  ↓
Database Writer
  ↓
TimescaleDB (time-series optimization)
  ↓
API Gateway (FastAPI) ← Trading Engine
```

**Core Services:**
- **Market Data**: WebSocket client for Pacifica, publishes to Redis
- **DB Writer**: Batch inserts (5000 ticks/batch) to TimescaleDB
- **API Gateway**: FastAPI REST endpoints (port 8000)
- **Trading Engine**: 5 algorithmic strategies with direct Pacifica API integration

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Installation

1. Clone and start services:
```bash
git clone https://github.com/nexwave-so/pacifica-operator.git
cd pacifica-operator
docker compose up -d --remove-orphans
```

2. Database will initialize automatically on first run

3. API Gateway available at `http://localhost:8000` (OpenAPI docs at `/docs`)

### Development

```bash
# Install dependencies
uv sync
source .venv/bin/activate

# Run services
python -m src.nexwave.services.market_data.client
python -m src.nexwave.services.db_writer.service
python -m src.nexwave.services.api_gateway.main
python -m src.nexwave.services.trading_engine.engine
```

## API Endpoints

### Market Data
- `GET /api/v1/pairs` - All 30 trading pairs configuration
- `GET /api/v1/latest-prices` - Real-time prices with 24h change
- `GET /api/v1/candles/{symbol}/{timeframe}` - OHLCV candles (1m, 5m, 15m, 1h, 4h, 1d)

### Trading
- `GET /api/v1/positions` - Current open positions
- `GET /api/v1/performance` - Strategy performance metrics
- `GET /api/analytics` - Analytics data

### Agent Integration (OpenClaw)
- `GET /api/v1/strategy-config` - Current strategy/risk parameters (safe, no secrets)
- `PATCH /api/v1/strategy-config` - Merge overrides; trading engine reloads every 60s (no restart). On your OpenClaw agent host (e.g., Nexbot): `~/.agent-name/docs/PACIFICA_OPERATOR_INTEGRATION.md`.

### WebSocket
- `WS /ws/market-data` - Real-time stream for all pairs

## Trading Strategies

**Pacifica Operator = dominant scalper** (5m timeframe, 1.5x/2.5x ATR SL/TP, 2x volume, 5 min cooldown). See [docs/SCALPING_STRATEGY.md](docs/SCALPING_STRATEGY.md).

**5 Active Strategies:**
1. **Short-Term Momentum** - 5m candles (configurable), scalping-oriented; reads from config
2. **Long-Term Momentum** - 1d candles, 10d lookback
3. **Momentum Short** - 1d candles, 14d lookback
4. **MR Long Hedge** - 1h candles, 20h lookback
5. **MR Short Hedge** - 1h candles, 14h lookback

**Risk Management:**
- Symbol blacklist: XPL, ASTER, FARTCOIN, PENGU, CRV, SUI
- Trade frequency: 5-min cooldown, max 10 trades/symbol/day
- Minimum position: $50 (eliminates fee bleeding)
- Volatility-adjusted take profit: 1-6x ATR based on volatility

## Configuration

Key environment variables in `.env`:

```bash
# Trading
PAPER_TRADING=false
PORTFOLIO_VALUE=50
VWM_MOMENTUM_THRESHOLD=0.001
VWM_VOLUME_MULTIPLIER=0.5

# Pacifica DEX
PACIFICA_API_URL=https://api.pacifica.fi/api/v1
PACIFICA_API_KEY=your_key_here
PACIFICA_AGENT_WALLET_PUBKEY=your_pubkey
PACIFICA_AGENT_WALLET_PRIVKEY=your_privkey

# Database
DATABASE_URL=postgresql://nexwave:password@postgres:5432/nexwave
REDIS_URL=redis://redis:6379
```

## 🚀 Performance

- **API Latency**: <50ms
- **Database Write**: 5,000+ ticks/second
- **Data Collection**: 30 concurrent symbol streams

## 🔧 Tech Stack

**Backend:** Python 3.11+, FastAPI, TimescaleDB, Redis, SQLAlchemy
**Infrastructure:** Docker, Solana

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Development context and critical updates
- **[Pairs Implementation](docs/PAIRS_IMPLEMENTATION.md)** - 30-pair support guide
- **OpenClaw Agent Integration** - On your agent host: `~/.agent-name/docs/PACIFICA_OPERATOR_INTEGRATION.md` (run `agent-skills-reload` after adding skills)

## Recent Updates (Jan 2026)

- ✅ **OpenClaw Integration**: GET/PATCH `/api/v1/strategy-config` for monitoring and plain-English tweaks; see `~/.agent-name/docs/PACIFICA_OPERATOR_INTEGRATION.md` on the agent host.
- ✅ **Backend-only architecture**: Removed frontend and NGINX (now API-first)
- ✅ Removed unused services: Kafka, Zookeeper, whale tracking, order management
- ✅ Reduced Docker footprint by 6+ containers (~800MB saved)
- ✅ Cleaned up 3,000+ lines of dead code
- ✅ Streamlined to 6 essential backend services
- ✅ Direct Pacifica API integration (no message queue overhead)

## 🔗 Links

- **Website**: [nexwave.so](https://nexwave.so)
- **GitHub**: [github.com/nexwave-so/pacifica-operator](https://github.com/nexwave-so/pacifica-operator)
- **Twitter**: [@nexwave_so](https://x.com/nexwave_so)

## License

MIT License

---

**Operated by Nexwave and an [OpenClaw](https://github.com/openclaw/openclaw) Agent** | Autonomous Trading on Solana
