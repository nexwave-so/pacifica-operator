# Trading System Readiness Check

## ✅ Configuration Status

Based on your setup:

1. **Wallet Keys**: ✅ Configured
   - Public Key: `<your_public_key>`
   - Private Key: ✅ Set (not displayed for security)

2. **Wallet Funds**: ✅ Loaded
   - SOL: Available
   - USDC: Available

3. **Trading Mode**: ⚠️ Currently in PAPER TRADING mode
   - To enable real trading, add to `.env`:
     ```
     PAPER_TRADING=false
     ```

## 🧪 Testing Options

### Option 1: Test with Existing Scripts (Recommended)

If you have the Python environment set up:

```bash
cd /var/www/nexwave

# Test wallet connection and system readiness
python scripts/test_order_placement.py

# For real trading test (interactive)
python scripts/test_real_trading.py
```

### Option 2: Test via Docker Services

If services are running in Docker:

```bash
cd /var/www/nexwave

# 1. Update .env to enable real trading
echo "PAPER_TRADING=false" >> .env

# 2. Restart order management service
docker compose restart order-management

# 3. Check logs to see if orders are being placed
docker compose logs -f order-management
```

### Option 3: Manual Test Order

Use the place_test_order script with real trading:

```bash
cd /var/www/nexwave

# Set real trading mode
export PAPER_TRADING=false

# Place a small test order (e.g., 0.1 SOL buy)
python scripts/place_test_order.py --symbol SOL --side bid --amount 0.1 --real
```

## 📋 Pre-Trading Checklist

Before enabling real trading:

- [x] Wallet keys configured
- [x] Wallet funded (SOL and USDC)
- [ ] Paper trading disabled (`PAPER_TRADING=false`)
- [ ] Services restarted to pick up new config
- [ ] Test with small amount first (0.1 SOL or less)
- [ ] Monitor logs for errors

## 🔍 Verification Steps

1. **Check Configuration**:
   ```bash
   grep -E "PAPER_TRADING|PACIFICA" .env
   ```

2. **Test Wallet Connection**:
   - The system should be able to connect to Pacifica API
   - Should be able to fetch current positions
   - Should be able to sign messages

3. **Test Order Placement**:
   - Start with a very small test order
   - Monitor order status
   - Check positions after order fills

## ⚠️ Important Notes

1. **Start Small**: Always test with minimal amounts first
2. **Monitor Logs**: Watch for errors in order placement
3. **Check Positions**: Verify orders are actually being placed
4. **Paper Trading**: Default is paper trading for safety - must explicitly disable

## 🚀 Next Steps

1. **Enable Real Trading**:
   ```bash
   echo "PAPER_TRADING=false" >> /var/www/nexwave/.env
   ```

2. **Restart Services** (if using Docker):
   ```bash
   docker compose restart order-management trading-engine
   ```

3. **Test Order Placement**:
   - Use one of the test scripts above
   - Or wait for strategy signals if trading engine is running

4. **Monitor**:
   - Check logs: `docker compose logs -f order-management`
   - Check positions on Pacifica DEX
   - Verify orders are being executed

## 📞 Troubleshooting

If orders aren't being placed:

1. Check `PAPER_TRADING=false` is set
2. Verify wallet keys are correct
3. Check API connection (test script)
4. Review error logs
5. Verify wallet has sufficient balance
6. Check risk manager isn't rejecting orders

