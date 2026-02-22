"""SQLAlchemy models for TimescaleDB"""

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Text,
    Double,
    Integer,
    JSON,
    DateTime,
    UniqueConstraint,
    Index,
    Column,
)
from sqlalchemy.sql import func
from nexwave.db.session import Base


class Tick(Base):
    """Tick data table - TimescaleDB hypertable"""

    __tablename__ = "ticks"

    time = Column(DateTime(timezone=True), nullable=False, primary_key=True)
    symbol = Column(Text(), nullable=False, primary_key=True)
    price = Column(Double(), nullable=False)
    volume = Column(Double(), nullable=False)
    bid = Column(Double(), nullable=True)
    ask = Column(Double(), nullable=True)
    exchange = Column(Text(), default="pacifica", nullable=False)

    __table_args__ = (
        Index("idx_ticks_symbol_time", "symbol", "time", postgresql_using="btree"),
        Index("idx_ticks_time_symbol", "time", "symbol", postgresql_using="btree"),
    )


class WhaleActivity(Base):
    """Whale activities table (DEPRECATED - not in use)"""

    __tablename__ = "whale_activities"

    id = Column(BigInteger().with_variant(BigInteger, "postgresql"), primary_key=True)
    detected_at = Column(DateTime(timezone=True), nullable=False)
    symbol = Column(Text(), nullable=False)
    whale_type = Column(Text(), nullable=False)  # 'single' or 'ladder'
    direction = Column(Text(), nullable=False)  # 'bid' or 'ask'
    price_low = Column(Double(), nullable=False)
    price_high = Column(Double(), nullable=False)
    total_volume = Column(Double(), nullable=False)
    total_value_usd = Column(Double(), nullable=False)
    order_count = Column(Integer(), nullable=False)
    confidence_score = Column(Double(), nullable=True)
    market_impact_bps = Column(Double(), nullable=True)
    meta = Column("metadata", JSON(), nullable=True)

    __table_args__ = (
        Index("idx_whale_symbol_detected", "symbol", "detected_at", postgresql_using="btree"),
        Index("idx_whale_value", "total_value_usd", postgresql_using="btree"),
        Index("idx_whale_detected", "detected_at", postgresql_using="btree"),
    )


class Order(Base):
    """Orders table - complete audit trail"""

    __tablename__ = "orders"

    id = Column(BigInteger().with_variant(BigInteger, "postgresql"), primary_key=True)
    order_id = Column(Text(), unique=True, nullable=False)
    client_order_id = Column(Text(), unique=True, nullable=True)
    strategy_id = Column(Text(), nullable=False)
    symbol = Column(Text(), nullable=False)
    side = Column(Text(), nullable=False)  # 'bid' or 'ask'
    order_type = Column(Text(), nullable=False)  # 'limit', 'market', etc.
    amount = Column(Double(), nullable=False)
    price = Column(Double(), nullable=True)
    filled_amount = Column(Double(), default=0.0, nullable=False)
    average_fill_price = Column(Double(), nullable=True)
    status = Column(Text(), nullable=False)  # 'open', 'filled', 'canceled', 'rejected'
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    filled_at = Column(DateTime(timezone=True), nullable=True)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    meta = Column("metadata", JSON(), nullable=True)

    __table_args__ = (
        Index("idx_orders_strategy_created", "strategy_id", "created_at", postgresql_using="btree"),
        Index("idx_orders_symbol_status_created", "symbol", "status", "created_at", postgresql_using="btree"),
        Index("idx_orders_status_created", "status", "created_at", postgresql_using="btree"),
    )


class Position(Base):
    """Positions table - current open positions"""

    __tablename__ = "positions"

    id = Column(BigInteger().with_variant(BigInteger, "postgresql"), primary_key=True)
    strategy_id = Column(Text(), nullable=False)
    symbol = Column(Text(), nullable=False)
    side = Column(Text(), nullable=False)  # 'long' or 'short'
    amount = Column(Double(), nullable=False)
    entry_price = Column(Double(), nullable=False)
    current_price = Column(Double(), nullable=True)
    unrealized_pnl = Column(Double(), nullable=True)
    realized_pnl = Column(Double(), default=0.0, nullable=False)
    trailing_stop_price = Column(Double(), nullable=True)  # Trailing stop level for advanced position management
    opened_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    meta = Column("metadata", JSON(), nullable=True)

    __table_args__ = (
        UniqueConstraint("strategy_id", "symbol", name="uq_positions_strategy_symbol"),
        Index("idx_positions_strategy_symbol", "strategy_id", "symbol", postgresql_using="btree"),
    )

