#!/usr/bin/env python3
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from nexwave.services.order_management.pacifica_client import PacificaClient

async def check():
    client = PacificaClient()
    positions = await client.get_positions()

    if isinstance(positions, dict) and 'data' in positions:
        pos_list = positions['data']
    elif isinstance(positions, list):
        pos_list = positions
    else:
        pos_list = []

    for p in pos_list:
        if p.get('symbol') == 'ZEC':
            print("✅ ZEC Position Found:")
            print(f"  Side: {p.get('side')}")
            print(f"  Amount: {p.get('amount')}")
            print(f"  Entry Price: ${p.get('entry_price')}")
            print(f"  Stop Loss: {p.get('stop_loss', 'N/A')}")
            print(f"  Take Profit: {p.get('take_profit', 'N/A')}")
            return

    print('No ZEC position found yet (order may still be executing)')

asyncio.run(check())
