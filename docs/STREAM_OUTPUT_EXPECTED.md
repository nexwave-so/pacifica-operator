# Expected Output from stream_premium.sh

## What You Should See

When you run `./stream_premium.sh`, you should see:

### 1. **Immediate Output (Header)**
```
   ███╗   ██╗███████╗██╗  ██╗██╗    ██╗ █████╗ ██╗   ██╗███████╗
   ████╗  ██║██╔════╝╚██╗██╔╝██║    ██║██╔══██╗██║   ██║██╔════╝
   ██╔██╗ ██║█████╗   ╚███╔╝ ██║ █╗ ██║███████║██║   ██║█████╗
   ██║╚██╗██║██╔══╝   ██╔██╗ ██║███╗██║██╔══██║╚██╗ ██╔╝██╔══╝
   ██║ ╚████║███████╗██╔╝ ██╗╚███╔███╔╝██║  ██║ ╚████╔╝ ███████╗
   ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝ ╚═╝  ╚═╝  ╚═══╝  ╚══════╝

        🚀 A U T O N O M O U S   T R A D I N G   A G E N T 🚀

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ⚡ STRATEGY        Volume-Weighted Momentum (VWM)
  💰 CAPITAL         $159 → $795-$1,590 (5x leverage)
  📊 MARKETS         30 Perpetual Pairs (Pacifica DEX)
  🎯 SIGNALS         0.1% momentum + 1.2x volume
  🛡️  RISK MGMT      Stop Loss (2.5x ATR) | Take Profit (5x ATR)
  🤖 STATUS          LIVE & SCANNING FOR OPPORTUNITIES

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                  📡 LIVE SIGNAL FEED - HACKATHON DEMO 📡

  Connecting to trading engine... Waiting for live activity...
```

### 2. **After Connection (Within 60 seconds)**

You should see one of these:

#### Option A: Market Scanning Activity
```
  [18:45:21] 🔄 Scanning all markets for opportunities...
  [18:45:21] BTC | VWM: ↑ 0.002219 | Vol: ✓ 1.5x | ATR: 0.11 | Candles: 25
  [18:45:21] ETH | VWM: → 0.000109 | Vol: ⚠ 0.92x | ATR: 0.05 | Candles: 25
      ⚠ Volume close: 0.92x (need 1.2x) - Waiting for volume spike...
  [18:45:22] SOL | VWM: ↓ -0.000383 | Vol: ⚠ 0.80x | ATR: 0.11 | Candles: 25
  ...
  [18:45:23] ✓ Scan complete. Next scan in 60s...
```

#### Option B: Signal Detected
```
═══════════════════════════════════════════════════════════════════

   🟢🟢🟢  B U Y   S I G N A L   D E T E C T E D  🟢🟢🟢

   ───────────────────────────────────────────────────────────────────

   SYMBOL:      BTC
   MOMENTUM:    +0.002219% (bullish trend detected)
   VOLUME:      1.5x average (high conviction)
   STRENGTH:    0.74 (normalized confidence)
   TIMESTAMP:   [18:45:21]

   ───────────────────────────────────────────────────────────────────
   ACTION: Calculating position size with 5x leverage...
═══════════════════════════════════════════════════════════════════
```

## If You See Nothing After Header

### Possible Reasons:

1. **Trading engine not running**
   ```bash
   docker ps | grep trading-engine
   # Should show container running
   ```

2. **Engine is between scan cycles**
   - Scans happen every 60 seconds
   - Wait up to 60 seconds for first activity

3. **No matching log patterns**
   - Check if engine is generating logs:
   ```bash
   docker logs nexwave-trading-engine --tail 10
   ```

4. **Container name mismatch**
   - Verify container name:
   ```bash
   docker ps | grep trading
   # Should show: nexwave-trading-engine
   ```

## Troubleshooting

### Check if engine is generating logs:
```bash
docker logs nexwave-trading-engine --tail 20 | grep -E "Signal Check|Processing"
```

### Check if container is running:
```bash
docker ps | grep trading-engine
```

### Restart the trading engine if needed:
```bash
cd /var/www/nexwave
docker compose restart trading-engine
```

### Test the script with a shorter timeout:
```bash
timeout 65 ./stream_premium.sh
# Should see activity within 60 seconds
```

## Expected Behavior

- **Header appears immediately** ✅
- **"Waiting for activity" message appears** ✅
- **Within 60 seconds:** Either scanning activity or signal detection
- **Continuous updates:** Every 60 seconds (scan cycle)
- **Statistics:** Every 10 symbols scanned

## Normal Operation

The script is **working correctly** if you see:
1. Header immediately
2. "Waiting for activity" message
3. Activity within 60 seconds (scanning or signals)

If you see the header but nothing else for more than 60 seconds, check the trading engine status.

