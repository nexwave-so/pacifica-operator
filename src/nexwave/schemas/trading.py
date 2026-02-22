"""Trading schemas"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class CreateOrderRequest(BaseModel):
    """Request to create an order"""

    strategy_id: str
    symbol: str
    side: str = Field(..., description="'bid' or 'ask'")
    order_type: str = Field(..., description="'limit' or 'market'")
    amount: float = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)
    reduce_only: bool = False
    client_order_id: Optional[str] = None


class OrderResponse(BaseModel):
    """Order response"""

    order_id: str
    status: str
    created_at: datetime


class Position(BaseModel):
    """Position data"""

    symbol: str
    side: str = Field(..., description="'long' or 'short'")
    amount: float
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None
    leverage: Optional[float] = None
    notional: Optional[float] = None  # Position size in USD
    quantity: Optional[float] = None
    hold_time_min: Optional[int] = None  # Hold time in minutes


class PositionsResponse(BaseModel):
    """Positions response"""

    positions: list[Position]

