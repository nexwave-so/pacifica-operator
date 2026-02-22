# Nexwave Testing Guide - Iteration 2

This guide provides instructions for testing each component implemented in Iteration 2.

## Prerequisites

1. Docker and Docker Compose installed
2. All services running via `docker compose up`
3. Database migrations applied
4. Environment variables configured in `.env` file

## 1. Whale Tracker Service Testing

### Start the Service

```bash
docker compose up whale-tracker
```

### Verify Service is Running

```bash
docker logs nexwave-whale-tracker -f
```

You should see logs like:
```
Starting Whale Tracker Service...
Symbols: ['BTC', 'ETH', 'SOL']
Detection interval: 5s
```

### Test Whale Detection

1. **Check Orderbook Data**: Ensure market-data service is publishing orderbook data to Redis:
   ```bash
   docker exec -it nexwave-redis redis-cli
   > KEYS orderbook:*
   > XREAD STREAMS orderbook:BTC $ COUNT 1
   ```

2. **Verify Database Storage**: Check if whales are being stored:
   ```bash
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave
   > SELECT * FROM whale_activities ORDER BY detected_at DESC LIMIT 5;
   ```

3. **Test Telegram Alerts** (if configured):
   - Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
   - Restart whale-tracker service
   - Verify alerts are sent when whales > threshold are detected

### Expected Behavior

- Service processes orderbook snapshots every 5 seconds
- Detects single-price-point whales (>1% of volume)
- Detects ladder patterns (3+ consecutive similar orders)
- Stores detections in database with confidence scores
- Sends alerts for whales > $25K USD (configurable)

## 2. TimescaleDB Continuous Aggregates Testing

### Apply Migrations

```bash
# Copy migration files to container
docker cp migrations/002_continuous_aggregates.sql nexwave-postgres:/tmp/
docker cp migrations/003_compression_policies.sql nexwave-postgres:/tmp/

# Execute migrations
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -f /tmp/002_continuous_aggregates.sql
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -f /tmp/003_compression_policies.sql
```

### Verify Continuous Aggregates

```bash
docker exec -it nexwave-postgres psql -U nexwave -d nexwave

# Check if views exist
> \dv candles_*

# Check data in 1-minute candles
> SELECT * FROM candles_1m_ohlcv WHERE symbol = 'BTC' ORDER BY time DESC LIMIT 10;

# Check refresh policies
> SELECT * FROM timescaledb_information.continuous_aggregates;
```

### Test API Endpoint

```bash
# Test candle endpoint
curl "http://localhost:8000/api/v1/candles/BTC/1h?limit=10"

# Should return OHLCV data from continuous aggregates
```

### Expected Behavior

- Candles are automatically generated at all timeframes (1m, 5m, 15m, 1h, 4h, 1d)
- 1-minute candles refresh every minute
- API endpoint returns data from materialized views (fast queries)
- Compression policies are active (older data is compressed)

## 3. Trading Engine Service Testing

### Start the Service

```bash
docker compose up trading-engine
```

### Verify Service is Running

```bash
docker logs nexwave-trading-engine -f
```

Expected logs:
```
Starting Trading Engine...
Strategy ID: mean_reversion_1
Paper Trading: True
Portfolio Value: $100,000.00
Initialized mean_reversion strategy for BTC
Initialized mean_reversion strategy for ETH
Initialized mean_reversion strategy for SOL
```

### Test Signal Generation

1. **Monitor Signal Generation**:
   ```bash
   docker logs nexwave-trading-engine -f | grep -i signal
   ```

2. **Check Database for Orders**:
   ```bash
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave
   > SELECT * FROM orders WHERE strategy_id = 'mean_reversion_1' ORDER BY created_at DESC LIMIT 5;
   ```

3. **Verify Risk Checks**:
   - Check logs for risk manager approvals/rejections
   - Verify position limits are enforced
   - Check daily loss limit behavior

### Test Risk Management

1. **Position Limit Test**:
   - Create multiple orders to exceed $1M position limit
   - Verify orders are rejected with appropriate reason

2. **Leverage Test**:
   - Create orders that would exceed 5x leverage
   - Verify leverage check rejects orders

3. **Daily Loss Limit Test**:
   - Simulate losses exceeding -5% daily limit
   - Verify trading is halted

### Expected Behavior

- Strategy generates signals based on mean reversion logic
- Risk manager validates all orders before submission
- Orders are sent to Kafka for processing
- Performance metrics are calculated (Sharpe, win rate, PnL)
- Paper trading mode simulates orders without real execution

## 4. Order Management Service Testing

### Start the Service

```bash
docker compose up order-management
```

### Verify Service is Running

```bash
docker logs nexwave-order-management -f
```

Expected logs:
```
Starting Order Management Service...
Paper Trading: True
Connected to Kafka consumer for order requests
Connected to Kafka producer for order events
```

### Test Order Processing (Paper Trading)

1. **Send Test Order Request to Kafka**:
   ```bash
   docker exec -it nexwave-kafka kafka-console-producer \
     --broker-list localhost:9092 \
     --topic order-requests
   
   # Paste this JSON:
   {
     "strategy_id": "mean_reversion_1",
     "symbol": "BTC",
     "side": "bid",
     "order_type": "market",
     "amount": 0.1,
     "client_order_id": "test-order-123",
     "paper_trading": true,
     "metadata": {"test": true}
   }
   ```

2. **Verify Order Processing**:
   ```bash
   docker logs nexwave-order-management -f
   # Should show order creation and processing
   ```

3. **Check Database**:
   ```bash
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave
   > SELECT * FROM orders ORDER BY created_at DESC LIMIT 5;
   ```

### Test Real Trading (Requires Wallet Keys)

**WARNING**: Only test with small amounts and a test wallet!

1. **Configure Real Trading**:
   ```bash
   # In .env file
   PAPER_TRADING=false
   PACIFICA_AGENT_WALLET_PRIVKEY=your_test_wallet_private_key
   PACIFICA_AGENT_WALLET_PUBKEY=your_test_wallet_public_key
   ```

2. **Restart Service**:
   ```bash
   docker compose restart order-management
   ```

3. **Send Order Request**:
   - Use the same Kafka producer method
   - Set `paper_trading: false` in order request
   - Monitor logs for Pacifica API calls

### Test Circuit Breaker

1. **Simulate API Failures**:
   - Temporarily disable Pacifica API URL
   - Send multiple order requests
   - Verify circuit breaker opens after 5 failures

2. **Verify Recovery**:
   - Restore API URL
   - Wait for timeout (60 seconds)
   - Verify service enters half-open state and resumes

### Expected Behavior

- Orders are received from Kafka
- Orders are signed using Solana keypair
- Orders are submitted to Pacifica API (or simulated in paper mode)
- Order status is tracked in database
- Order events are published to Kafka
- Circuit breaker protects against API failures
- Order state is reconciled every 60 seconds

## 5. Integration Testing

### End-to-End Flow Test

1. **Start All Services**:
   ```bash
   docker compose up -d --remove-orphans
   ```

2. **Verify Data Flow**:
   - Market data → Redis → Database Writer → TimescaleDB
   - Orderbook → Whale Tracker → Database → Alerts
   - Market data → Trading Engine → Signals → Order Requests → Kafka
   - Order Requests → Order Management → Pacifica API → Database

3. **Check All Services are Healthy**:
   ```bash
   docker compose ps
   ```

4. **Monitor Logs**:
   ```bash
   docker compose logs -f
   ```

### API Testing

1. **Test Candle Endpoint**:
   ```bash
   curl "http://localhost:8000/api/v1/candles/BTC/1h?limit=10"
   ```

2. **Test Whale Endpoint**:
   ```bash
   curl "http://localhost:8000/api/v1/whales?min_value_usd=25000&limit=10"
   ```

3. **Test Positions Endpoint**:
   ```bash
   curl "http://localhost:8000/api/v1/positions?strategy_id=mean_reversion_1"
   ```

## 6. Performance Testing

### Load Testing

1. **Candle Query Performance**:
   ```bash
   time curl "http://localhost:8000/api/v1/candles/BTC/1h?limit=1000"
   ```

2. **Database Query Performance**:
   ```bash
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave
   > EXPLAIN ANALYZE SELECT * FROM candles_1h_ohlcv WHERE symbol = 'BTC' ORDER BY time DESC LIMIT 100;
   ```

### Monitoring

1. **Check Service Resources**:
   ```bash
   docker stats
   ```

2. **Monitor Database Size**:
   ```bash
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave
   > SELECT pg_size_pretty(pg_database_size('nexwave'));
   ```

## 7. Troubleshooting

### Common Issues

1. **Whale Tracker Not Detecting Whales**:
   - Check if orderbook data is being published to Redis
   - Verify orderbook format matches expected structure
   - Check detection threshold (may be too high)

2. **Candles Not Being Generated**:
   - Verify migrations are applied
   - Check if tick data exists in database
   - Verify continuous aggregate policies are active

3. **Trading Engine Not Generating Signals**:
   - Check if candles data is available
   - Verify market data is being received
   - Check strategy parameters (may need adjustment)

4. **Order Management Not Processing Orders**:
   - Verify Kafka is running and accessible
   - Check Kafka topics exist
   - Verify order requests are being sent to correct topic

### Debug Commands

```bash
# Check Redis keys
docker exec -it nexwave-redis redis-cli KEYS "*"

# Check Kafka topics
docker exec -it nexwave-kafka kafka-topics --list --bootstrap-server localhost:9092

# Check database connections
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -c "SELECT count(*) FROM pg_stat_activity;"

# View recent logs
docker compose logs --tail=100 --follow
```

## 8. Success Criteria

✅ All services start without errors  
✅ Whale Tracker detects and stores whale activities  
✅ Candles are generated at all timeframes automatically  
✅ Trading Engine generates signals based on strategy  
✅ Order Management processes order requests  
✅ API endpoints return data from continuous aggregates  
✅ Paper trading mode works correctly  
✅ Logs show proper structured output  

## Next Steps

After verifying all components work correctly:

1. Configure monitoring and alerting
2. Set up production environment variables
3. Enable real trading (if ready, with proper safeguards)
4. Optimize performance based on testing results
5. Prepare for Iteration 3 development

