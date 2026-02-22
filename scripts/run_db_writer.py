#!/usr/bin/env python3
"""Entry point for Database Writer Service"""

import asyncio
from nexwave.services.db_writer.service import run_db_writer_service

if __name__ == "__main__":
    asyncio.run(run_db_writer_service())

