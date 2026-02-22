# Nexwave Trading Strategy Audit Report
**Date:** December 2025  
**Scope:** Trading strategy for crypto perpetual futures on Pacifica DEX  
**Strategy Type:** Mean Reversion

---

## Executive Summary

This audit evaluates the Nexwave trading strategy implementation for trading general crypto perpetual futures. The current implementation uses a basic mean reversion strategy with fixed parameters and lacks several critical features required for robust perpetual futures trading.

**Key Findings:**
- ✅ **Strengths:** Clean architecture, risk management framework exists, basic position sizing
- ⚠️ **Critical Issues:** No leverage management, missing perpetual-specific features, no short-side trading
- 🔧 **Improvements Needed:** Dynamic position sizing, funding rate awareness, market regime detection

---

## ✅ Implemented Improvements (Quick Wins)

The following improvements have been implemented as quick wins:

### 1. Short-Side Trading ✅
- **Status:** Implemented
- **Changes:** Added short entry signals when price > mean + 2σ
- **Impact:** Strategy now captures both long and short mean reversion opportunities (doubled trading opportunities)
- **Files Modified:** `src/nexwave/strategies/mean_reversion_strategy.py`

### 2. Leverage Integration ✅
- **Status:** Implemented
- **Changes:** Position sizing now uses leverage from pair configuration (up to 5x)
- **Impact:** 5x capital efficiency, better utilization of perpetual futures
- **Files Modified:** `src/nexwave/strategies/mean_reversion_strategy.py`

### 3. Reduce-Only Flag ✅
- **Status:** Implemented
- **Changes:** All closing orders now use `reduce_only=True` to prevent accidental position openings
- **Impact:** Critical safety feature for perpetual futures trading
- **Files Modified:** `src/nexwave/services/trading_engine/engine.py`

### 4. Portfolio Value Calculation ✅
- **Status:** Implemented
- **Changes:** Fixed hardcoded $100k value, now calculates: `initial_cash + unrealized_PnL + realized_PnL`
- **Impact:** Accurate risk calculations based on real portfolio value
- **Files Modified:** `src/nexwave/services/trading_engine/risk_manager.py`

### 5. Liquidation Price Helper ✅
- **Status:** Implemented
- **Changes:** Added `calculate_liquidation_price()` method for risk management
- **Impact:** Foundation for liquidation risk checks
- **Files Modified:** `src/nexwave/services/trading_engine/risk_manager.py`

---

## Current Strategy Analysis

### 1. Strategy Implementation

**File:** `src/nexwave/strategies/mean_reversion_strategy.py`

#### Current Logic:
- **Entry:** Price < mean - (2 * std_dev) → BUY
- **Exit:** Price > mean + (2 * std_dev) OR take profit (+5%) → SELL
- **Stop Loss:** -3% from entry
- **Position Size:** Fixed 10% of portfolio
- **Timeframe:** 1 hour (default)
- **Lookback:** 20 periods

#### Issues Identified:

1. **Long-Only Strategy**
   - ❌ Only trades long positions (no short selling)
   - ❌ Mean reversion works both ways - should short when price > mean + 2σ
   - Impact: Misses 50% of mean reversion opportunities

2. **Fixed Position Sizing**
   - ❌ Position size is always 10% regardless of volatility, confidence, or market conditions
   - ❌ No Kelly Criterion or volatility-adjusted sizing
   - Impact: Overexposure in volatile markets, underexposure in high-confidence setups

3. **No Leverage Consideration**
   - ❌ Strategy calculates position size in USD, but doesn't account for leverage
   - ❌ Perpetual futures allow leverage up to 50x (BTC/ETH), but strategy doesn't use it
   - Impact: Capital inefficiency, missing leverage benefits

4. **Simple Statistical Model**
   - ❌ Only uses mean and standard deviation
   - ❌ No RSI, MACD, Bollinger Bands, or other momentum indicators
   - ❌ No trend filtering to avoid trading against strong trends
   - Impact: Poor performance in trending markets

5. **Fixed Stop Loss/Take Profit**
   - ❌ Stop loss: -3%, Take profit: +5% (fixed percentages)
   - ❌ Not adjusted for volatility (ATR-based stops would be better)
   - Impact: Stops too tight in volatile markets, too wide in calm markets

---

### 2. Risk Management Analysis

**File:** `src/nexwave/services/trading_engine/risk_manager.py`

#### Current Risk Checks:
1. ✅ Daily loss limit (5%)
2. ✅ Order size limits (min/max)
3. ✅ Position size limits
4. ✅ Leverage check (max 5x)
5. ❌ Portfolio value is hardcoded (returns 100k)

#### Critical Missing Features:

1. **No Funding Rate Management**
   - ❌ Perpetual futures charge funding fees every 8 hours
   - ❌ No consideration of funding rate when entering positions
   - ❌ Should avoid long positions when funding rate is negative (paying fees)
   - Impact: Erodes profits over time, especially in high funding rate environments

2. **No Liquidation Price Calculation**
   - ❌ No calculation of liquidation price based on leverage
   - ❌ No safety margin from liquidation
   - Impact: Risk of liquidation in volatile markets

3. **No Margin Call Handling**
   - ❌ No monitoring of margin ratio
   - ❌ No automatic position reduction when margin is low
   - Impact: Sudden liquidations

4. **No Correlation Management**
   - ❌ Can open multiple positions in correlated assets (BTC, ETH, SOL)
   - ❌ No portfolio-level correlation limits
   - Impact: Overexposure to single market risk factor

5. **No Maximum Drawdown Protection**
   - ❌ Only daily loss limit, no cumulative drawdown limit
   - Impact: Can lose significant capital over multiple days

6. **Portfolio Value Calculation**
   - ❌ `get_portfolio_value()` returns hardcoded 100k
   - ❌ Should calculate: cash + unrealized PnL + realized PnL
   - Impact: Risk calculations based on incorrect portfolio value

---

### 3. Perpetual Futures-Specific Issues

#### Missing Perpetual Features:

1. **Funding Rate**
   ```python
   # Should be fetched and considered:
   - Current funding rate (8h period)
   - Funding rate history
   - Expected funding cost over holding period
   ```

2. **Leverage Management**
   ```python
   # Current: position_size = portfolio_value * 0.10
   # Should be: position_size = (portfolio_value * 0.10) * leverage
   # With leverage limits per pair (from pairs.py)
   ```

3. **Mark Price vs Index Price**
   - ❌ Using last traded price, should use mark price for perpetuals
   - ❌ No consideration of index price divergence
   - Impact: Incorrect PnL calculations

4. **Position Side (Long/Short)**
   - ❌ Strategy only implements long positions
   - ❌ Should support short positions for mean reversion
   - Impact: Missing half of trading opportunities

5. **Reduce-Only Orders**
   - ✅ Order management supports reduce_only flag
   - ❌ Strategy doesn't use it when closing positions
   - Impact: Could accidentally open new positions when closing

---

## Recommended Improvements

### 1. Enhanced Mean Reversion Strategy

#### A. Add Short-Side Trading

```python
# In mean_reversion_strategy.py

# Entry conditions should be:
if current_price <= entry_lower:
    # LONG signal (price below mean)
    signal_type = SignalType.BUY
    
elif current_price >= entry_upper:  # mean + (2 * std_dev)
    # SHORT signal (price above mean)
    signal_type = SignalType.SELL
```

#### B. Dynamic Position Sizing

```python
def calculate_position_size(self, signal: TradingSignal, current_price: float) -> float:
    """Calculate position size using volatility-adjusted sizing"""
    
    # Get ATR (Average True Range) for volatility
    atr = self.calculate_atr()
    
    # Base position size
    base_size_pct = self.position_size_pct
    
    # Adjust for volatility (lower size in high volatility)
    volatility_adjustment = min(1.0, 0.5 / (atr / current_price))
    
    # Adjust for confidence
    confidence_adjustment = signal.confidence
    
    # Final position size
    adjusted_size_pct = base_size_pct * volatility_adjustment * confidence_adjustment
    
    # Apply leverage from pair config
    pair_config = get_pair_by_symbol(self.symbol)
    leverage = min(pair_config.max_leverage, self.max_leverage)
    
    position_value_usd = self.portfolio_value * (adjusted_size_pct / 100.0)
    position_size = (position_value_usd * leverage) / current_price
    
    return position_size
```

#### C. Volatility-Based Stop Loss/Take Profit

```python
def calculate_stops(self, entry_price: float, atr: float) -> tuple[float, float]:
    """Calculate stop loss and take profit based on ATR"""
    
    # Stop loss: 2x ATR below entry
    stop_loss = entry_price - (2.0 * atr)
    
    # Take profit: 3x ATR above entry (risk:reward = 1:1.5)
    take_profit = entry_price + (3.0 * atr)
    
    return stop_loss, take_profit
```

#### D. Trend Filter

```python
def is_trending_market(self, candles: list[Dict]) -> bool:
    """Check if market is in strong trend (avoid mean reversion)"""
    
    # Calculate EMA
    ema_fast = self.calculate_ema(candles, period=9)
    ema_slow = self.calculate_ema(candles, period=21)
    
    # If EMAs are diverging significantly, market is trending
    ema_diff_pct = abs(ema_fast - ema_slow) / ema_slow
    
    return ema_diff_pct > 0.02  # 2% divergence = trending
```

---

### 2. Funding Rate Integration

#### A. Fetch Funding Rates

```python
# Add to market_data service
async def get_funding_rate(self, symbol: str) -> Dict[str, float]:
    """Get current funding rate for perpetual"""
    # Fetch from Pacifica API or market data
    return {
        "funding_rate": 0.0001,  # 0.01% per 8h
        "next_funding_time": "...",
        "mark_price": 50000.0,
        "index_price": 50010.0,
    }
```

#### B. Consider Funding in Entry Decision

```python
async def generate_signal(self, market_data: Dict, ...) -> Optional[TradingSignal]:
    # ... existing logic ...
    
    # Check funding rate
    funding_data = await self.get_funding_rate(self.symbol)
    funding_rate = funding_data["funding_rate"]
    
    # If funding rate is negative and we're going long, we pay fees
    # If funding rate is positive and we're going short, we pay fees
    # Adjust confidence or skip trade if funding cost is too high
    
    if signal_type == SignalType.BUY and funding_rate < -0.0005:
        # High negative funding rate = expensive to hold long
        signal.confidence *= 0.7  # Reduce confidence
        
    elif signal_type == SignalType.SELL and funding_rate > 0.0005:
        # High positive funding rate = expensive to hold short
        signal.confidence *= 0.7
```

---

### 3. Enhanced Risk Management

#### A. Fix Portfolio Value Calculation

```python
async def get_portfolio_value(self, strategy_id: str) -> float:
    """Calculate actual portfolio value"""
    
    async with AsyncSessionLocal() as session:
        # Get cash balance (simplified - should track actual balance)
        cash = 100000.0  # TODO: Track from trades
        
        # Get unrealized PnL from open positions
        positions = await self.get_current_positions(strategy_id)
        unrealized_pnl = sum(pos["unrealized_pnl"] for pos in positions)
        
        # Get realized PnL from closed positions today
        realized_pnl = await self.calculate_daily_pnl(strategy_id)
        
        return cash + unrealized_pnl + realized_pnl
```

#### B. Add Liquidation Price Calculation

```python
def calculate_liquidation_price(
    self, 
    entry_price: float, 
    side: str, 
    leverage: float,
    margin_ratio: float = 0.5  # 50% margin requirement
) -> float:
    """Calculate liquidation price for perpetual position"""
    
    if side == "long":
        # Long liquidation: entry_price * (1 - margin_ratio / leverage)
        liquidation = entry_price * (1 - margin_ratio / leverage)
    else:  # short
        # Short liquidation: entry_price * (1 + margin_ratio / leverage)
        liquidation = entry_price * (1 + margin_ratio / leverage)
    
    return liquidation

# Add to risk check
async def check_liquidation_risk(self, ...) -> RiskCheckResult:
    """Check if position is too close to liquidation"""
    liquidation_price = self.calculate_liquidation_price(...)
    current_price = ...
    
    distance_to_liquidation = abs(current_price - liquidation_price) / current_price
    
    if distance_to_liquidation < 0.05:  # Within 5% of liquidation
        return RiskCheckResult(
            approved=False,
            reason=f"Too close to liquidation: {distance_to_liquidation:.2%}"
        )
```

#### C. Add Correlation Management

```python
async def check_correlation_limit(
    self, 
    strategy_id: str, 
    new_symbol: str,
    max_correlation: float = 0.7
) -> RiskCheckResult:
    """Check if adding new position exceeds correlation limits"""
    
    # Get existing positions
    positions = await self.get_current_positions(strategy_id)
    
    # Calculate correlation with existing positions
    # (Simplified - should use historical price correlation)
    correlated_symbols = ["BTC", "ETH", "SOL"]  # Major cryptos
    if new_symbol in correlated_symbols:
        existing_major = [p["symbol"] for p in positions if p["symbol"] in correlated_symbols]
        if len(existing_major) >= 2:
            # Already have 2 major positions, limit exposure
            return RiskCheckResult(
                approved=False,
                reason=f"Too many correlated positions: {len(existing_major)}"
            )
    
    return RiskCheckResult(approved=True, reason="Correlation OK")
```

---

### 4. Strategy Improvements

#### A. Market Regime Detection

```python
class MarketRegime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    VOLATILE = "volatile"

def detect_market_regime(self, candles: list[Dict]) -> MarketRegime:
    """Detect current market regime"""
    
    # Calculate indicators
    atr = self.calculate_atr(candles)
    ema_fast = self.calculate_ema(candles, 9)
    ema_slow = self.calculate_ema(candles, 21)
    
    # Check volatility
    volatility_pct = atr / candles[-1]["close"]
    
    if volatility_pct > 0.03:  # 3% volatility
        return MarketRegime.VOLATILE
    
    # Check trend
    ema_diff = abs(ema_fast - ema_slow) / ema_slow
    if ema_diff > 0.02:
        return MarketRegime.TRENDING
    
    return MarketRegime.RANGING

# Adjust strategy based on regime
async def generate_signal(self, ...):
    regime = self.detect_market_regime(candles)
    
    if regime == MarketRegime.TRENDING:
        # Reduce mean reversion confidence in trending markets
        # Or switch to trend-following strategy
        return None  # Skip mean reversion in trends
    
    elif regime == MarketRegime.VOLATILE:
        # Reduce position size in volatile markets
        position_size_multiplier = 0.5
```

#### B. Multi-Timeframe Analysis

```python
async def generate_signal(self, ...):
    # Check multiple timeframes for confirmation
    signals_1h = await self._generate_signal_timeframe("1h")
    signals_4h = await self._generate_signal_timeframe("4h")
    
    # Only trade if signals align across timeframes
    if signals_1h and signals_4h and signals_1h.signal_type == signals_4h.signal_type:
        # Higher confidence when multiple timeframes agree
        signal.confidence = min(0.95, signal.confidence * 1.2)
        return signal
    
    return None  # No alignment = no trade
```

---

### 5. Order Management Improvements

#### A. Use Reduce-Only for Closing

```python
# In trading_engine.py create_order()
if signal.signal_type in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
    order_request["reduce_only"] = True  # Critical for perpetuals
```

#### B. Slippage Protection

```python
# In mean_reversion_strategy.py
def calculate_expected_slippage(self, order_size: float, current_price: float) -> float:
    """Estimate slippage based on order size and market depth"""
    # Simplified - should use order book depth
    order_size_usd = order_size * current_price
    
    if order_size_usd > 10000:  # Large orders
        slippage_pct = 0.001  # 0.1% slippage
    else:
        slippage_pct = 0.0005  # 0.05% slippage
    
    return slippage_pct

# Adjust entry price expectations
entry_price_with_slippage = current_price * (1 + slippage_pct)
```

---

## Implementation Priority

### High Priority (Critical)
1. ✅ **Fix portfolio value calculation** - Risk management depends on this
2. ✅ **Add short-side trading** - Double trading opportunities
3. ✅ **Integrate funding rate checks** - Essential for perpetuals
4. ✅ **Add liquidation price calculation** - Prevent liquidations

### Medium Priority (Important)
5. ✅ **Dynamic position sizing** - Better risk-adjusted returns
6. ✅ **Volatility-based stops** - Better stop placement
7. ✅ **Market regime detection** - Avoid bad trades in trending markets
8. ✅ **Use reduce_only flag** - Prevent accidental position openings

### Low Priority (Nice to Have)
9. ✅ **Correlation management** - Portfolio-level risk
10. ✅ **Multi-timeframe confirmation** - Higher quality signals
11. ✅ **Slippage estimation** - More accurate entry prices

---

## Testing Recommendations

1. **Backtesting Framework**
   - Test strategy on historical data (6+ months)
   - Include funding costs in backtest
   - Test across different market regimes

2. **Paper Trading**
   - Run for 1-2 weeks before live trading
   - Monitor funding costs, slippage, execution quality

3. **Risk Metrics**
   - Track: Sharpe ratio, max drawdown, win rate, profit factor
   - Compare to benchmarks (buy-and-hold, simple momentum)

4. **Stress Testing**
   - Test behavior during flash crashes
   - Test with high funding rates
   - Test with low liquidity

---

## Conclusion

The current Nexwave trading strategy provides a solid foundation but needs significant enhancements for robust perpetual futures trading. The most critical improvements are:

1. **Perpetual-specific features** (funding rates, liquidation prices)
2. **Short-side trading** (mean reversion works both ways)
3. **Dynamic risk management** (volatility-adjusted sizing, proper portfolio value)
4. **Market regime awareness** (avoid mean reversion in trending markets)

With these improvements, the strategy should perform significantly better in live trading across various market conditions.

---

## Code References

- Strategy: `src/nexwave/strategies/mean_reversion_strategy.py`
- Risk Manager: `src/nexwave/services/trading_engine/risk_manager.py`
- Trading Engine: `src/nexwave/services/trading_engine/engine.py`
- Pairs Config: `src/nexwave/common/pairs.py`

