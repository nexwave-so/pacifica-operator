# Live Trading Configuration - December 6, 2025

## Configuration Update

Switched from **paper trading** to **live trading on mainnet** with a conservative $50 USDC portfolio for initial testing.

## Changes Applied

### Trading Mode
- **PAPER_TRADING**: `true` → `false`
- **Environment**: Paper trading → Live mainnet

### Portfolio Settings
- **PORTFOLIO_VALUE**: `100000` → `50`
- **Currency**: USDC on Pacifica perpetual DEX (Solana)

### Position Sizing Adjustments
- **VWM_BASE_POSITION_PCT**: `12.0%` → `100.0%`
- **VWM_MAX_POSITION_PCT**: `18.0%` → `100.0%`

**Rationale**: With $50 portfolio and $50 minimum position size (per risk management rules), only 1 position can be held at a time. Adjusted to 100% position sizing to reflect this constraint.

## Current Trading Configuration

### Portfolio
- **Total Capital**: $50 USDC
- **Max Positions**: 1 (due to $50 minimum position size)
- **Position Size**: 100% portfolio per trade

### Trading Pairs (5 Active)
- BTC (Bitcoin)
- ETH (Ethereum)
- BNB (Binance Coin)
- SOL (Solana)
- ZEC (Zcash)

### Blacklisted Symbols (Risk Management)
Per CLAUDE.md risk management rules, the following symbols are blocked due to poor historical performance:
- XPL (-$176 combined losses)
- ASTER
- FARTCOIN
- PENGU
- CRV
- SUI

### Strategy Parameters
- **Strategy**: Volume Weighted Momentum (VWM)
- **Strategy ID**: vwm_momentum_1
- **Momentum Threshold**: 0.15%
- **Exit Threshold**: 0.10%
- **Volume Multiplier**: 0.3x
- **Lookback Period**: 20 candles

### Risk Management
- **Max Leverage**: 5x
- **Daily Loss Limit**: 5%
- **Minimum Position Size**: $50
- **Trade Frequency**: 5-min cooldown, max 10 trades/symbol/day
- **Profit Viability**: Rejects trades requiring >5% move or <$2 profit after fees

## Verification

### Trading Engine Status
```
[INFO] Starting Trading Engine...
[INFO] Strategy ID: vwm_momentum_1
[INFO] Paper Trading: False ✅
[INFO] Portfolio Value: $50 ✅
```

### Order Management Status
```
[INFO] Initialized Pacifica client with wallet: HVXrj9PFN5sLqkvWhs5quGsQHKsbaeb75sroPtTiCUWU ✅
[INFO] Paper Trading: False ✅
```

### Pacifica Connection
```
[INFO] ✅ Connected to Pacifica API for order placement
[INFO] Position sync complete: 0 active, 0 updated, 0 created, 0 deleted
```

## Important Notes

### Fund Safety
⚠️ **Live Trading Active**: Real USDC will be used for trades on Pacifica mainnet
- Ensure wallet has at least $50 USDC available
- Check wallet balance before signal generation starts
- Monitor positions closely during initial testing phase

### Position Limitations
With $50 portfolio:
- Can only hold **1 position at a time**
- Each position will use **$50 (100% of portfolio)**
- Cannot diversify across multiple assets simultaneously
- Strategy will be highly concentrated

### Expected Behavior
- **Signal Generation**: Starts after ~1 hour more data collection (20-24 candles needed)
- **Trade Frequency**: Max 10 trades per symbol per day
- **Position Duration**: Varies based on strategy exit conditions
- **P&L Tracking**: Real-time sync with Pacifica API every 60s

### Scaling Considerations
To enable multiple positions:
- **$100 portfolio**: 2 positions possible (2 × $50 minimum)
- **$250 portfolio**: 5 positions possible (1 per trading pair)
- **$500 portfolio**: More flexible position sizing (10-20% per position)

Current configuration optimized for minimal capital risk during testing phase.

## Rollback Instructions

To revert to paper trading:

1. Update `.env`:
   ```bash
   PAPER_TRADING=true
   PORTFOLIO_VALUE=100000
   VWM_BASE_POSITION_PCT=12.0
   VWM_MAX_POSITION_PCT=18.0
   ```

2. Export and restart:
   ```bash
   export PAPER_TRADING=true
   export PORTFOLIO_VALUE=100000
   docker compose up -d --no-deps --force-recreate trading-engine order-management
   ```

## Related Documentation

- `docs/2025-12-06_pacifica-wallet-setup.md` - Wallet configuration
- `docs/diagnostics/2025-12-06_trading-engine-status.md` - Engine health check
- `CLAUDE.md` - Risk management rules and trading parameters

## Status

**Configuration**: ✅ Complete and verified
**Trading Mode**: 🔴 **LIVE** (mainnet)
**Portfolio**: $50 USDC
**Positions**: 0 active (waiting for signals)
**Date**: 2025-12-06
**Time**: 21:00 UTC

---

*Live trading enabled. Monitor closely during initial operation.*
