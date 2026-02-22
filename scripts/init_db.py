#!/usr/bin/env python3
"""Initialize database schema"""

import asyncio
import os
from sqlalchemy import text
from nexwave.db.session import engine, Base
from nexwave.db import models  # Import models to register them


async def init_db():
    """Initialize database schema"""
    print("Creating database tables...")

    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Tables created")

        # Convert ticks to hypertable
        try:
            await conn.execute(
                text(
                    "SELECT create_hypertable('ticks', 'time', "
                    "chunk_time_interval => INTERVAL '1 day', "
                    "if_not_exists => TRUE)"
                )
            )
            print("✓ Ticks hypertable created")
        except Exception as e:
            print(f"Note: Hypertable creation: {e}")

        # Create indexes
        print("✓ All database objects created successfully")


if __name__ == "__main__":
    asyncio.run(init_db())
