#!/usr/bin/env python3
"""
Test end-to-end trading flow: signal → order creation → Pacifica execution
"""

import asyncio
import json
import sys
import uuid
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from nexwave.common.logger import setup_logging, logger
from kafka import KafkaProducer


async def test_end_to_end():
    """Test the complete trading pipeline"""
    setup_logging(level="INFO")

    print("\n" + "="*70)
    print("END-TO-END TRADING FLOW TEST")
    print("="*70)

    # Initialize Kafka producer
    print("\n1. Connecting to Kafka...")
    try:
        producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        print("   ✅ Connected to Kafka")
    except Exception as e:
        print(f"   ❌ Failed to connect to Kafka: {e}")
        return False

    # Create test order request
    order_request = {
        "strategy_id": "test_end_to_end",
        "symbol": "SOL",
        "side": "bid",  # BUY
        "order_type": "market",
        "amount": 0.1,  # 0.1 SOL (~$25)
        "price": None,
        "reduce_only": False,
        "client_order_id": f"test-e2e-{uuid.uuid4()}",
        "paper_trading": False,  # REAL ORDER
        "metadata": {
            "source": "end_to_end_test",
            "signal_type": "buy",
            "confidence": 0.85,
        },
    }

    print("\n2. Order Details:")
    print(f"   Symbol: {order_request['symbol']}")
    print(f"   Side: {order_request['side']} (BUY)")
    print(f"   Amount: {order_request['amount']} SOL")
    print(f"   Type: {order_request['order_type']}")
    print(f"   Paper Trading: {order_request['paper_trading']}")

    print("\n⚠️  WARNING: This will place a REAL order on Pacifica DEX!")
    print(f"   Estimated value: ~${order_request['amount'] * 250:.2f}")

    response = input("\n   Continue? (yes/no): ")
    if response.lower() != "yes":
        print("   Test cancelled")
        producer.close()
        return False

    # Send order to Kafka
    print("\n3. Sending order to Kafka (order-requests topic)...")
    try:
        future = producer.send(
            "order-requests",
            value=order_request,
        )
        result = future.get(timeout=10)
        print(f"   ✅ Order sent to Kafka")
        print(f"   → Topic: {result.topic}")
        print(f"   → Partition: {result.partition}")
        print(f"   → Offset: {result.offset}")
    except Exception as e:
        print(f"   ❌ Failed to send order: {e}")
        producer.close()
        return False

    producer.close()

    print("\n4. Monitoring order-management service...")
    print("   Check logs: docker logs -f nexwave-order-management")
    print("   Check Pacifica UI for order execution")

    print("\n" + "="*70)
    print("✅ Test complete! Order sent to order management service")
    print("="*70)
    print("\nNext steps:")
    print("1. Monitor order-management logs for order creation")
    print("2. Check Pacifica UI for order appearing in the orderbook")
    print("3. Verify order fills and position updates")
    print()

    return True


if __name__ == "__main__":
    success = asyncio.run(test_end_to_end())
    sys.exit(0 if success else 1)
