# Trading Engine Status

Quick reference for verifying the Nexwave Trading Engine with a funded Pacifica wallet (e.g. ~$15 USDC for testing).

## Current Service Status

- **Postgres** – healthy  
- **Redis** – healthy  
- **API Gateway** – healthy (port 8000)  
- **DB Writer** – healthy (writes ticks to TimescaleDB)  
- **Market Data** – WebSocket connected to Pacifica (health check may show unhealthy; service is working)  
- **Trading Engine** – running; position sync and live orders require agent wallet keypair  

## Enabling Live Trading With Your Funded Wallet

To use the wallet where you added ~$15 USDC:

1. **Set the Agent Wallet in `.env`**  
   The engine needs the **Solana keypair** for the wallet that holds the USDC (not the API key from the UI):

   - `PACIFICA_AGENT_WALLET_PUBKEY` – public key of that wallet  
   - `PACIFICA_AGENT_WALLET_PRIVKEY` – private key (full keypair, ~88 chars base58)  

   See [docs/AGENT_WALLET_SETUP.md](AGENT_WALLET_SETUP.md) for how to generate or obtain this keypair and register it in Pacifica.

2. **Turn off paper trading** (optional, for real orders):

   ```bash
   PAPER_TRADING=false
   ```

3. **Restart the trading engine** so it picks up env and keypair:

   ```bash
   docker compose up -d --build --no-deps trading-engine
   ```

4. **Check logs** – you should see position sync and no “Keypair not initialized”:

   ```bash
   docker logs nexwave-trading-engine --tail 80
   ```

## “Not enough candle data” Warnings

Strategies need a minimum number of candles (e.g. 24 for 1h, more for 1d). After a fresh deploy or empty DB, you will see:

- `Not enough candle data for BTC/ETH/...`  
- `Not enough candle data to detect regime`  
- Market regime defaulting to `SIDEWAYS`  

This is expected. Once the market-data → db-writer pipeline has been running for the required time (see CLAUDE.md for approximate hours/days), strategies will start producing signals.

## Quick Checks

```bash
# Container status
docker compose ps -a

# Trading engine logs
docker logs nexwave-trading-engine --tail 100

# API health and positions
curl -s http://localhost:8000/health
curl -s http://localhost:8000/positions
```

## Summary

- **Engine is running**: 60s signal loop, risk manager, strategies, circuit breakers.  
- **Position sync and live orders** require `PACIFICA_AGENT_WALLET_PRIVKEY` (and `PACIFICA_AGENT_WALLET_PUBKEY`) set to the funded wallet’s keypair.  
- **Candle warnings** will clear once enough history is collected; no code change needed.
