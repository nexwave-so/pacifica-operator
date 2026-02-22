# High-Momentum Quality Trading Strategy

**Date Implemented**: November 15, 2025
**Portfolio Size**: $435
**Philosophy**: Quality over quantity - wait for the best setups, then go big

---

## Strategy Overview

### Core Principle
Instead of taking many small trades with marginal profits, we focus on **high-momentum explosive moves** that justify larger position sizes. Think of it as "sniper trading" - wait patiently for the perfect shot.

### Why This Works for Small Portfolios

With a $435 portfolio and 0.14% round-trip fees:
- **Old approach**: 30 signals/day at $35 each → $0.10-$0.30 profit per trade → $3-$9 daily (before losses)
- **New approach**: 3-5 signals/day at $65-$87 each → $0.80-$2.50 profit per trade → $2.40-$12.50 daily (concentrated)

**Key insight**: You can't afford to be wrong 20 times. Better to be right 3 times.

---

## New Parameters

### Signal Generation (Tightened by 2-4x)

```bash
VWM_MOMENTUM_THRESHOLD=0.004    # 0.4% - Only explosive momentum (was 0.2%)
VWM_EXIT_THRESHOLD=0.0015       # 0.15% - Let winners run longer (was 0.08%)
VWM_VOLUME_MULTIPLIER=0.5       # 0.5x - Require decent volume (was 0.3x)
VWM_LOOKBACK_PERIOD=20          # 20 candles - unchanged
```

**What this means**:
- Only pairs showing 4x normal momentum threshold get traded
- Recent winners: MON (0.44%), ZEC (0.41%), WLFI (0.18% - now excluded)
- Expect 2-6 signals per day (down from 20-40)

### Position Sizing (Increased by 1.9-1.7x)

```bash
VWM_BASE_POSITION_PCT=15.0      # 15% base - $65.25 per trade (was $35)
VWM_MAX_POSITION_PCT=20.0       # 20% max - $87 on strongest signals (was $52)
```

**What this means**:
- Base trades now $65 (3.8x trading fees = $0.09 fee cost)
- Max trades now $87 (5x trading fees = $0.12 fee cost)
- Need only 0.15% profit to break even (down from 0.14% seems small, but it's about absolute dollars)
- Each 1% move = $0.65-$0.87 profit (vs $0.35-$0.52 before)

### Risk Management (Adjusted for Aggressive Approach)

```bash
MAX_CONCURRENT_POSITIONS=3      # Max 3 positions (was 8)
DAILY_LOSS_LIMIT_PCT=10         # 10% max loss (was 8%)
```

**What this means**:
- Focus on your best 3 setups at any time
- 65% of portfolio can be deployed (3 × $87 = $261 max)
- Remaining 35% ($174) stays as cash buffer
- $43.50 max daily loss (acceptable with higher position sizes)

---

## Trade Examples

### Previous Strategy (Low Threshold)
```
Example: LINK at $14.50
VWM: 0.15% (met old 0.2% threshold with rounding)
Volume: 0.76x average (passes 0.3x filter)
Position: $35 (8% base)
Profit target: $14.65 (1.0% = $0.35)
Fees: $0.049
Net profit: $0.30

Result: Trade taken, but profit barely covers slippage risk
```

### New Strategy (High Threshold)
```
Example: MON at $0.0470
VWM: 0.43% (meets 0.4% threshold!)
Volume: 0.84x average (passes 0.5x filter)
Position: $65.25 (15% base)
Profit target: $0.0494 (5.1% = $3.33)
Fees: $0.091
Net profit: $3.24

Result: Trade taken, high conviction, meaningful profit
```

### Rejected Trade Under New Strategy
```
Example: WLFI at $0.35
VWM: 0.18% (below 0.4% threshold - REJECTED)
Volume: 0.78x average (would pass volume filter)
Position: Would be $65.25

Result: No trade. Wait for better setup.
```

---

## Expected Performance

### Frequency
- **Signals generated**: 2-6 per day (scan 30 pairs × 24 hours ÷ strict filters)
- **Positions entered**: 2-5 per day (MAX_CONCURRENT_POSITIONS=3 limits entries)
- **Average hold time**: 2-6 hours (high momentum = faster moves)

### Profitability
- **Win rate target**: 50-60% (quality signals have higher success rate)
- **Average win**: $2.50-$4.00 (5-8% moves on $65-$87 positions)
- **Average loss**: -$1.30-$2.17 (2-3% stop loss on $65-$87 positions)
- **Risk/Reward**: 1.9:1 (good for momentum strategy)

### Daily P&L Expectations
```
Conservative scenario (2 trades/day, 50% win rate):
1 win × $2.50 + 1 loss × -$1.30 = +$1.20/day (+0.28% ROI)
Monthly: +$36 (+8.3% ROI)

Moderate scenario (4 trades/day, 55% win rate):
2.2 wins × $3.00 + 1.8 losses × -$1.50 = +$3.90/day (+0.90% ROI)
Monthly: +$117 (+26.9% ROI)

Aggressive scenario (6 trades/day, 60% win rate):
3.6 wins × $3.50 + 2.4 losses × -$1.80 = +$8.28/day (+1.90% ROI)
Monthly: +$248 (+57% ROI)
```

**Reality check**: Expect conservative to moderate performance. Aggressive scenario requires perfect market conditions.

---

## Risk Analysis

### What Could Go Wrong

1. **Too Few Signals** (Most Likely Risk)
   - If market is ranging (low momentum), may go 6-12 hours without signals
   - Solution: 0.4% threshold might be too strict. Can lower to 0.3% if needed.

2. **Larger Losses** (Acceptable Risk)
   - $65 position × 2% stop loss = -$1.30 loss (vs -$0.70 before)
   - With 3 concurrent positions, max exposure = $261 (60% of portfolio)
   - Max drawdown if all 3 hit stop loss: -$3.90 (-0.90% portfolio)

3. **Correlation Risk** (Mitigated)
   - High-momentum pairs often move together (e.g., all meme coins pump)
   - MAX_CONCURRENT_POSITIONS=3 limits this
   - Directional bias check prevents 3 long positions in same sector

### Safety Mechanisms

- **Daily loss limit**: Trading stops at -10% (-$43.50)
- **Position limit**: Max $100 per position (23% of portfolio)
- **Leverage cap**: 3x maximum (conservative for perpetuals)
- **Stop losses**: 2.5x ATR (typically 2-4% for high-vol pairs)

---

## Monitoring & Adjustments

### Key Metrics to Track

1. **Signal frequency**: Should see 2-6 signals/day
   - If <2/day: Lower threshold to 0.003 (0.3%)
   - If >10/day: Raise threshold to 0.005 (0.5%)

2. **Win rate**: Aim for 50-60%
   - If <45%: Increase VWM_VOLUME_MULTIPLIER to 0.6
   - If >65%: You're being too conservative, lower threshold

3. **Average profit per trade**: Target $2-$4
   - Track: (Sum of realized PnL) / (Number of closed trades)
   - If <$1.50: Position sizes too small OR profit targets too tight

4. **Capital utilization**: Aim for 40-60% deployed
   - Calculate: (Sum of open position values) / (Portfolio value)
   - If <30%: Too few trades, lower threshold slightly

### Weekly Review Process

Every Monday, review:
- Total trades last week (target: 14-35)
- Win rate (target: 50-60%)
- Total P&L (target: +2-5% weekly)
- Largest winner (should be >$5)
- Largest loser (should be <$3)

Adjust thresholds accordingly.

---

## Technical Implementation

### Files Changed

1. **`.env`**:
   - `VWM_MOMENTUM_THRESHOLD`: 0.002 → 0.004
   - `VWM_EXIT_THRESHOLD`: 0.0008 → 0.0015
   - `VWM_VOLUME_MULTIPLIER`: 0.3 → 0.5
   - `VWM_BASE_POSITION_PCT`: 8.0 → 15.0
   - `VWM_MAX_POSITION_PCT`: 12.0 → 20.0
   - `MAX_CONCURRENT_POSITIONS`: 8 → 3
   - `DAILY_LOSS_LIMIT_PCT`: 8 → 10

2. **`risk_manager.py`**:
   - Fixed hardcoded portfolio value ($100K → uses PORTFOLIO_VALUE env var)
   - Now correctly calculates leverage and risk limits for $435 portfolio

3. **`volume_weighted_momentum_strategy.py`**:
   - Added ATR fallback (2% of price) for zero-ATR pairs
   - Prevents TP/SL calculation errors on low-priced tokens

### Deployment

```bash
# Restart trading engine to pick up new parameters
docker compose restart trading-engine

# Watch logs to verify new thresholds
docker logs -f nexwave-trading-engine | grep "Signal Check"

# You should see:
# - "VWM=0.00XXX (threshold=±0.004)" instead of 0.002
# - Fewer signals being generated
# - Larger position sizes when trades are taken
```

---

## Rollback Plan

If this strategy doesn't work (e.g., too few signals for 24+ hours):

```bash
# Revert to previous strategy in .env
VWM_MOMENTUM_THRESHOLD=0.002
VWM_EXIT_THRESHOLD=0.0008
VWM_VOLUME_MULTIPLIER=0.3
VWM_BASE_POSITION_PCT=8.0
VWM_MAX_POSITION_PCT=12.0
MAX_CONCURRENT_POSITIONS=8

# Then restart
docker compose restart trading-engine
```

**When to rollback**:
- <3 signals in 24 hours (too restrictive)
- Win rate <40% after 20+ trades (poor signal quality)
- Daily P&L consistently negative for 5+ days

---

## Success Criteria

After 7 days of trading, this strategy is successful if:

1. ✅ **Profitability**: Total P&L > +$20 (+4.6% return)
2. ✅ **Win rate**: 48-65% (quality signals)
3. ✅ **Average profit**: >$2 per winning trade
4. ✅ **Risk management**: No single loss >$3
5. ✅ **Consistency**: At least 2 trades per day

If 4 out of 5 criteria met → Continue strategy
If <3 criteria met → Revert or adjust thresholds

---

**Last Updated**: November 15, 2025
**Strategy Author**: Nexwave Trading Team
**Review Date**: November 22, 2025
