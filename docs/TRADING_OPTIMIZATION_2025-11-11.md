# Trading Engine Optimization - November 11, 2025

## Summary

Optimized trading parameters for **$435 portfolio** focusing on profitability over demo activity. Strategy shifted from high-frequency/low-quality to fewer, higher-quality setups with larger position sizes to overcome fees.

## Portfolio Status

**Pacifica Account:**
- **Account Equity:** $435.29
- **Idle Balance:** $357.54
- **Active Positions:** 22 positions (~$78 deployed)
- **Unrealized P&L:** +$9.37 (+2.15%)
- **Cross Leverage:** 1.51x
- **Maintenance Margin:** $39.47

**Performance Snapshot (First Hour After Hackathon):**
- All 22 positions profitable (GREEN)
- Best performer: ZEC (-6.56% short, +$2.54 profit)
- Average hold time: <1 minute (just opened)
- No closed trades yet to analyze win rate

## Problem Identified

**Previous Configuration (Hackathon Mode):**
- Optimized for **volume/activity**, not profitability
- 22 concurrent positions = spreading capital too thin
- Small position sizes ($22-39 avg) barely cover 0.04% maker fees
- Volume threshold too loose (0.10x) = accepting poor liquidity
- Momentum threshold too low (0.1%) = catching noise

**Key Issue:** With $435 portfolio and 22 positions, average position is $35. At 0.04% fees, need 0.08% move just to break even ($0.028). Small positions don't give trades room to breathe.

## Optimization Strategy

### **Core Philosophy:**
**Quality over quantity.** Focus on 5-8 high-conviction setups rather than 20-30 marginal trades.

### **Position Sizing Math:**

| Portfolio | Position % | Position $ | Notional (3x lev) | Break-even Move | Target Move |
|-----------|-----------|-----------|-------------------|-----------------|-------------|
| $435 | 8% | $35 | $105 | 0.08% | 2%+ |
| $435 | 12% | $52 | $156 | 0.08% | 2%+ |

**With 8-12% positions:**
- Large enough to overcome fees with meaningful profits
- 8 max positions = $280-420 deployed (64-97% of capital)
- Diversified enough to manage risk
- Concentrated enough for impact

### **Fee Optimization:**

**Pacifica Fees:** 0.04% maker / 0.015% taker

**Break-even calculations:**
- $35 position: $0.014 fees (maker) = need 0.04% move
- $52 position: $0.021 fees (maker) = need 0.04% move
- **Target:** 2% moves = 50x fee coverage = comfortable profit

**Strategy:** Larger positions + higher momentum threshold (0.2%) = fewer but profitable trades.

## Configuration Changes

### **1. Portfolio Value**

```bash
# BEFORE:
PORTFOLIO_VALUE=159

# AFTER:
PORTFOLIO_VALUE=435  # Updated to actual account equity
```

### **2. Position Sizing**

```bash
# BEFORE:
VWM_BASE_POSITION_PCT=3.0   # $13 positions (too small)
VWM_MAX_POSITION_PCT=5.0    # $22 positions (too small)

# AFTER:
VWM_BASE_POSITION_PCT=8.0   # $35 positions (meaningful)
VWM_MAX_POSITION_PCT=12.0   # $52 positions (strong signals)
```

**Rationale:**
- 8% base = minimum viable position size after fees
- 12% max = reward high-confidence setups
- Dynamic scaling: weak signals get 8%, strong get 12%

### **3. Signal Quality Filters**

```bash
# BEFORE:
VWM_MOMENTUM_THRESHOLD=0.001  # 0.1% - too sensitive, catching noise
VWM_EXIT_THRESHOLD=0.0005     # 0.05% - exits too early
VWM_VOLUME_MULTIPLIER=0.10    # 0.10x - accepting ultra-thin liquidity
VWM_LOOKBACK_PERIOD=15        # 15 candles - less data

# AFTER:
VWM_MOMENTUM_THRESHOLD=0.002  # 0.2% - higher quality signals
VWM_EXIT_THRESHOLD=0.0008     # 0.08% - let winners run longer
VWM_VOLUME_MULTIPLIER=0.3     # 0.3x - require better liquidity
VWM_LOOKBACK_PERIOD=20        # 20 candles - more robust signals
```

**Impact:**
- 0.2% momentum = ~2x threshold increase = 50-70% fewer signals
- 0.3x volume = ~3x stricter = avoid slippage on thin books
- More candles = better trend confirmation

### **4. Risk Management**

```bash
# BEFORE:
MAX_POSITION_SIZE_USD=1000000  # No real limit
MAX_LEVERAGE=5                 # Too high for small account
DAILY_LOSS_LIMIT_PCT=5         # $8 loss limit (1 bad trade)

# AFTER:
MAX_POSITION_SIZE_USD=100      # Hard cap at $100 per position (23%)
MAX_LEVERAGE=3                 # Conservative for live trading
DAILY_LOSS_LIMIT_PCT=8         # $35 loss limit (more breathing room)
```

**NEW:** Max concurrent positions limit

```bash
MAX_CONCURRENT_POSITIONS=8     # Focus on best 8 setups, not all 30 pairs
```

**Code Implementation:**
```python
# src/nexwave/services/trading_engine/engine.py:903-910
# Check max concurrent positions limit
max_positions = int(os.getenv("MAX_CONCURRENT_POSITIONS", "999"))
if len(all_positions) >= max_positions:
    logger.warning(
        f"⚠️  Skipping {signal.signal_type.value} signal for {symbol}: "
        f"Max concurrent positions reached ({len(all_positions)}/{max_positions})"
    )
    continue
```

## Expected Trading Behavior

### **Before Optimization:**
- **Frequency:** 20-50 trades/hour across all 30 pairs
- **Position size:** $22-39 per trade
- **Concurrent positions:** 15-25
- **Signal quality:** Mixed (accepting 0.1% momentum)
- **Goal:** Hackathon demo activity

### **After Optimization:**
- **Frequency:** 3-8 trades/hour (best setups only)
- **Position size:** $35-52 per trade
- **Concurrent positions:** 5-8 max
- **Signal quality:** High (requiring 0.2% momentum + 0.3x volume)
- **Goal:** Profitability and capital preservation

### **Profit Targets:**

**Conservative:** 10% monthly return
- $435 × 10% = $43.50/month
- $1.45/day average

**Realistic:** 15-20% monthly return
- $435 × 15% = $65/month
- $2.17/day average

**Aggressive:** 25%+ monthly return (if strategy performs well)
- $435 × 25% = $109/month
- $3.63/day average

**With 3-8 trades/day @ 8-12% position sizes, target 1-2% average gain per trade:**
- 5 trades/day × $40 avg position × 2% = $4/day = $120/month = **27% monthly return**

## Signal Quality Analysis

### **Current Market Conditions (23:56 UTC):**

Looking at latest scan with new parameters:

| Symbol | VWM | Volume | Threshold | Result |
|--------|-----|--------|-----------|--------|
| UNI | -0.27% | 0.17x | ±0.2%, 0.3x | ❌ Volume too low |
| LINK | -0.12% | 0.17x | ±0.2%, 0.3x | ❌ Both below threshold |
| CRV | -0.15% | 0.16x | ±0.2%, 0.3x | ❌ Volume too low |
| PENGU | -0.11% | 0.21x | ±0.2%, 0.3x | ❌ Momentum too low |

**Result:** Zero signals generated in first scan - **GOOD!**

This is exactly what we want:
- Not taking marginal 0.1-0.15% moves
- Waiting for volume to pick up (0.3x threshold)
- Being patient for high-quality setups

**Next likely trade:** When market volume returns (typically 12:00-20:00 UTC) and we see 0.2%+ moves with 0.3x+ volume.

## Monitoring & Next Steps

### **Key Metrics to Track:**

**Daily:**
```bash
# Check open positions
docker exec nexwave-postgres psql -U nexwave -d nexwave \
  -c "SELECT symbol, side, amount, entry_price, unrealized_pnl
      FROM positions
      ORDER BY unrealized_pnl DESC;"

# Check closed trades performance
docker exec nexwave-postgres psql -U nexwave -d nexwave \
  -c "SELECT COUNT(*) as trades,
             SUM(realized_pnl) as total_pnl,
             AVG(realized_pnl) as avg_pnl,
             COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) as wins,
             COUNT(CASE WHEN realized_pnl < 0 THEN 1 END) as losses
      FROM positions
      WHERE realized_pnl <> 0
        AND updated_at > NOW() - INTERVAL '24 hours';"
```

**Weekly:**
```bash
# Win rate by pair
docker exec nexwave-postgres psql -U nexwave -d nexwave \
  -c "SELECT symbol,
             COUNT(*) as trades,
             SUM(realized_pnl) as total_pnl,
             AVG(realized_pnl) as avg_pnl,
             COUNT(CASE WHEN realized_pnl > 0 THEN 1 END) * 100.0 / COUNT(*) as win_rate_pct
      FROM positions
      WHERE realized_pnl <> 0
        AND updated_at > NOW() - INTERVAL '7 days'
      GROUP BY symbol
      ORDER BY total_pnl DESC
      LIMIT 10;"
```

### **Performance Evaluation Timeline:**

**Week 1 (Nov 12-18):**
- Let optimized strategy run
- Track: daily P&L, win rate, avg position size
- Goal: Validate 10-15% weekly return potential

**Week 2-3 (Nov 19-Dec 1):**
- Analyze which pairs performing best
- Consider cutting worst 10 pairs, focus on top 10
- Fine-tune momentum/volume thresholds based on data

**Week 4+ (December):**
- If profitable: consider scaling to $600-800
- If breaking even: iterate on entry/exit logic
- If losing: pivot or reduce to $200 for testing

### **Iteration Opportunities:**

**If Win Rate < 50%:**
- Increase momentum threshold to 0.25% (even more selective)
- Increase volume threshold to 0.5x (better liquidity)
- Focus on top 10 pairs only

**If Win Rate > 60% but Profits Small:**
- Increase position sizes to 10-15%
- Let winners run longer (exit threshold 0.10%)
- Add trailing stop losses

**If Too Few Trades (<2/day):**
- Lower momentum threshold to 0.15%
- Lower volume threshold to 0.25x
- Add time-of-day filters (trade during peak hours only)

## Risk Considerations

### **Current Risk Profile:**

**Positive:**
- ✅ Conservative leverage (1.51x actual, 3x max)
- ✅ Position size caps ($100 max = 23% of account)
- ✅ Daily loss limit (8% = $35)
- ✅ Max 8 concurrent positions (prevents over-diversification)
- ✅ Diversified across multiple pairs
- ✅ Stop losses active (2.5x ATR)

**Risks:**
- ⚠️ Small account size = high volatility
- ⚠️ Limited data (no closed trades yet)
- ⚠️ Untested win rate for new parameters
- ⚠️ Fees still significant (0.04-0.08% round trip)

**Mitigation:**
- Start conservative, scale gradually
- Track every trade for 1-2 weeks before increasing capital
- Set calendar reminder to review after 50-100 closed trades
- Don't add capital until proven profitable

### **Maximum Risk Scenarios:**

**Single Trade:**
- Max position: $52 × 3x leverage = $156 notional
- Stop loss: 2.5x ATR (typically 2-4%)
- Max loss: ~$3-6 per trade

**Daily:**
- 8% daily loss limit = $35 max
- ~6-10 losing trades would hit limit
- Circuit breaker prevents further trading

**Account Drawdown:**
- If account drops to $400: pause and analyze
- If account drops to $350 (-20%): serious evaluation needed
- If account drops to $300 (-30%): stop trading, revise strategy

## Files Modified

### **Configuration:**
- `.env:49` - PORTFOLIO_VALUE: 159 → 435
- `.env:22-25` - MAX_POSITION_SIZE_USD, MAX_LEVERAGE, DAILY_LOSS_LIMIT_PCT, MAX_CONCURRENT_POSITIONS
- `.env:53-58` - All VWM strategy parameters updated

### **Code:**
- `src/nexwave/services/trading_engine/engine.py:903-910` - Added MAX_CONCURRENT_POSITIONS check

### **Documentation:**
- `TRADING_OPTIMIZATION_2025-11-11.md` - This file (new)

## Complete Parameter Reference

### **Current Optimized Configuration:**

```bash
# Portfolio
PORTFOLIO_VALUE=435

# Risk Management
MAX_POSITION_SIZE_USD=100          # 23% of portfolio max
MAX_LEVERAGE=3                     # Conservative for $435
DAILY_LOSS_LIMIT_PCT=8             # $35 max daily loss
MAX_CONCURRENT_POSITIONS=8         # Focus on best setups

# VWM Strategy
VWM_MOMENTUM_THRESHOLD=0.002       # 0.2% - quality signals
VWM_EXIT_THRESHOLD=0.0008          # 0.08% - let winners run
VWM_VOLUME_MULTIPLIER=0.3          # 0.3x - require liquidity
VWM_LOOKBACK_PERIOD=20             # 20 candles - robust data
VWM_BASE_POSITION_PCT=8.0          # 8% = $35 positions
VWM_MAX_POSITION_PCT=12.0          # 12% = $52 strong signals
```

### **Previous Hackathon Configuration (for reference):**

```bash
# Portfolio
PORTFOLIO_VALUE=159

# Risk Management
MAX_POSITION_SIZE_USD=1000000      # Essentially unlimited
MAX_LEVERAGE=5                     # Aggressive
DAILY_LOSS_LIMIT_PCT=5             # $8 max daily loss
MAX_CONCURRENT_POSITIONS=(none)    # No limit

# VWM Strategy
VWM_MOMENTUM_THRESHOLD=0.001       # 0.1% - high frequency
VWM_EXIT_THRESHOLD=0.0005          # 0.05% - quick exits
VWM_VOLUME_MULTIPLIER=0.10         # 0.10x - ultra permissive
VWM_LOOKBACK_PERIOD=15             # 15 candles - fast signals
VWM_BASE_POSITION_PCT=3.0          # 3% = $5-13 positions
VWM_MAX_POSITION_PCT=5.0           # 5% = $8-22 positions
```

## Expected Outcomes

### **Short Term (1-7 days):**
- Trading frequency drops 70-80% (from 20-50 to 3-8 trades/day)
- Fewer positions open concurrently (5-8 vs 20-25)
- First batch of closed trades provides win rate data
- P&L should be positive if strategy is sound

### **Medium Term (1-4 weeks):**
- Accumulate 50-100 closed trades
- Calculate true win rate and average profit per trade
- Identify best-performing pairs (cut the rest)
- Optimize entry/exit thresholds based on data

### **Long Term (1-3 months):**
- If profitable (10-20% monthly): scale to $600-1000
- If marginal (0-5% monthly): keep iterating with $435
- If unprofitable (<0%): pivot strategy or shut down

## Success Criteria

### **After 1 Week:**
- [ ] At least 20 closed trades
- [ ] Win rate >45%
- [ ] Positive total P&L (even $5-10 is good start)
- [ ] No days hitting 8% loss limit

### **After 1 Month:**
- [ ] At least 100 closed trades
- [ ] Win rate >50%
- [ ] Monthly return >10% ($43+)
- [ ] Ready to scale to $600-800

### **After 3 Months:**
- [ ] Win rate >55%
- [ ] Consistent monthly returns (10-20%)
- [ ] Portfolio grown to $500-600 through profits
- [ ] Ready to scale to $1000-2000

## Conclusion

Shifted from **hackathon demo mode** (high volume, small positions) to **profitability mode** (selective, meaningful positions). Key changes:

1. **Portfolio updated** - $159 → $435 (actual equity)
2. **Position sizing increased** - 3-5% → 8-12% ($35-52 per trade)
3. **Signal quality improved** - 0.1%/0.1x → 0.2%/0.3x thresholds
4. **Position limits added** - Max 8 concurrent positions
5. **Risk management tightened** - $100 max position, 3x max leverage

**Next critical milestone:** First 50 closed trades will tell us if this strategy is truly profitable or needs further iteration.

**Status:** ✅ **OPTIMIZED AND RUNNING**

---

**Document Created:** November 11, 2025, 23:58 UTC
**Portfolio Size:** $435.29
**Optimization Goal:** Profitability over activity
**Author:** Trading Engine Optimization
**Last Modified:** November 11, 2025, 23:58 UTC
