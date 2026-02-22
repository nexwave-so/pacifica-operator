# Trading Scripts

This directory contains utility scripts for testing and managing the Nexwave trading system.

## Order Placement Testing

### test_order_placement.py

Comprehensive test suite to validate order placement capabilities.

**Usage:**
```bash
cd /var/www/nexwave
python scripts/test_order_placement.py
```

**What it tests:**
- Environment configuration (Pacifica credentials, API keys)
- Pair configuration validation
- Order validation logic
- Pacifica API connection
- Order creation flow

**Output:**
- Detailed test results for each component
- Clear error messages if something is misconfigured
- Recommendations for fixing issues

### place_test_order.py

Manually place a test order without waiting for strategy signals.

**Usage:**
```bash
# Place a paper trading order (default)
python scripts/place_test_order.py --symbol BTC --side bid --amount 0.001

# Place a real order (requires wallet)
python scripts/place_test_order.py --symbol BTC --side bid --amount 0.001 --real

# Place a limit order
python scripts/place_test_order.py --symbol ETH --side bid --amount 0.01 --type limit --price 2500
```

**Options:**
- `--symbol`: Trading symbol (BTC, ETH, SOL, etc.)
- `--side`: `bid` (buy) or `ask` (sell)
- `--amount`: Order amount in base currency
- `--type`: `market` or `limit`
- `--price`: Price for limit orders
- `--paper`: Force paper trading mode
- `--real`: Force real trading mode (requires wallet configured)

**Examples:**
```bash
# Buy 0.001 BTC with market order (paper trading)
python scripts/place_test_order.py --symbol BTC --side bid --amount 0.001

# Sell 0.1 ETH with limit order at $2500 (real trading)
python scripts/place_test_order.py --symbol ETH --side ask --amount 0.1 --type limit --price 2500 --real

# Test with small amount
python scripts/place_test_order.py --symbol SOL --side bid --amount 0.1
```

## Troubleshooting

### "Keypair not initialized"
- Check `PACIFICA_AGENT_WALLET_PRIVKEY` environment variable is set
- Verify the private key is in base58 format
- Ensure the key is valid (not the placeholder value)

### "Paper trading mode enabled"
- The system defaults to paper trading for safety
- Set `PAPER_TRADING=false` in environment to enable real trading
- Or use `--real` flag with `place_test_order.py`

### "No market data available"
- Check that market data service is running
- Verify Redis connection
- Check that data is being written to database

### "Order rejected by risk manager"
- Check daily loss limits
- Verify position size limits
- Review leverage settings

## Environment Variables

Key environment variables for order placement:

```bash
# Pacifica DEX Configuration
PACIFICA_API_URL=https://api.pacifica.fi/api/v1
PACIFICA_WS_URL=wss://ws.pacifica.fi/ws
PACIFICA_API_KEY=your_api_key
PACIFICA_AGENT_WALLET_PUBKEY=your_wallet_public_key
PACIFICA_AGENT_WALLET_PRIVKEY=your_wallet_private_key

# Trading Mode
PAPER_TRADING=true  # Set to false for real trading

# Risk Management
MAX_LEVERAGE=5
DAILY_LOSS_LIMIT_PCT=5
MAX_POSITION_SIZE_USD=1000000
```

## Next Steps

After verifying order placement works:

1. **Test paper trading orders** - Ensure orders are being created and stored
2. **Verify real trading setup** - Test with small amounts first
3. **Monitor order execution** - Check order status and fills
4. **Review risk limits** - Ensure they're appropriate for your strategy

