#!/usr/bin/env python3
"""Entry point for Market Data Service"""

import asyncio
from nexwave.services.market_data.client import run_market_data_service

if __name__ == "__main__":
    asyncio.run(run_market_data_service())

