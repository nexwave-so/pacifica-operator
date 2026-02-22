"""Trading pairs configuration for Pacifica DEX"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class PairCategory(str, Enum):
    """Category classification for trading pairs"""
    MAJOR = "major"
    MID_CAP = "mid-cap"
    EMERGING = "emerging"
    SMALL_CAP = "small-cap"


@dataclass
class PairConfig:
    """Configuration for a single trading pair"""
    symbol: str
    quote_asset: str
    max_leverage: int
    min_order_size: float
    tick_size: float
    display_name: str
    category: PairCategory
    is_active: bool = True
    whale_threshold_usd: Optional[float] = None  # Override default threshold


# All Pacifica DEX trading pairs (30 pairs as of November 2025)
PAIRS: List[PairConfig] = [
    # Major Pairs (High Volume)
    PairConfig(
        symbol="BTC",
        quote_asset="USD",
        max_leverage=50,
        min_order_size=0.001,
        tick_size=0.1,
        display_name="Bitcoin",
        category=PairCategory.MAJOR,
        whale_threshold_usd=25000,
    ),
    PairConfig(
        symbol="ETH",
        quote_asset="USD",
        max_leverage=50,
        min_order_size=0.01,
        tick_size=0.01,
        display_name="Ethereum",
        category=PairCategory.MAJOR,
        whale_threshold_usd=25000,
    ),
    PairConfig(
        symbol="SOL",
        quote_asset="USD",
        max_leverage=20,
        min_order_size=0.1,
        tick_size=0.001,
        display_name="Solana",
        category=PairCategory.MAJOR,
        whale_threshold_usd=25000,
    ),

    # Mid-Cap Pairs
    PairConfig(
        symbol="HYPE",
        quote_asset="USD",
        max_leverage=20,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="Hyperliquid",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="ZEC",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.01,
        tick_size=0.01,
        display_name="Zcash",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="BNB",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.01,
        tick_size=0.01,
        display_name="BNB",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="XRP",
        quote_asset="USD",
        max_leverage=20,
        min_order_size=10.0,
        tick_size=0.0001,
        display_name="Ripple",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="PUMP",
        quote_asset="USD",
        max_leverage=5,
        min_order_size=100.0,
        tick_size=0.00001,
        display_name="Pump",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="AAVE",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.1,
        tick_size=0.01,
        display_name="Aave",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),
    PairConfig(
        symbol="ENA",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=10.0,
        tick_size=0.0001,
        display_name="Ethena",
        category=PairCategory.MID_CAP,
        whale_threshold_usd=10000,
    ),

    # Emerging Pairs
    PairConfig(
        symbol="ASTER",
        quote_asset="USD",
        max_leverage=5,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="Aster",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="kBONK",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=100.0,
        tick_size=0.000001,
        display_name="Bonk (1000x)",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="kPEPE",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=100.0,
        tick_size=0.000001,
        display_name="Pepe (1000x)",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="LTC",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.1,
        tick_size=0.01,
        display_name="Litecoin",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="PAXG",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.01,
        tick_size=0.1,
        display_name="Paxos Gold",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="VIRTUAL",
        quote_asset="USD",
        max_leverage=5,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="Virtual",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="SUI",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="Sui",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="FARTCOIN",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.00001,
        display_name="Fartcoin",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="TAO",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=0.1,
        tick_size=0.01,
        display_name="Bittensor",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="DOGE",
        quote_asset="USD",
        max_leverage=15,
        min_order_size=10.0,
        tick_size=0.00001,
        display_name="Dogecoin",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="XPL",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="XPL",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="AVAX",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.01,
        display_name="Avalanche",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="LINK",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.001,
        display_name="Chainlink",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),
    PairConfig(
        symbol="UNI",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.001,
        display_name="Uniswap",
        category=PairCategory.EMERGING,
        whale_threshold_usd=5000,
    ),

    # Small-Cap Pairs
    PairConfig(
        symbol="WLFI",
        quote_asset="USD",
        max_leverage=5,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="WLFI",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
    PairConfig(
        symbol="PENGU",
        quote_asset="USD",
        max_leverage=5,
        min_order_size=100.0,
        tick_size=0.000001,
        display_name="Pengu",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
    PairConfig(
        symbol="2Z",
        quote_asset="USD",
        max_leverage=3,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="2Z",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
    PairConfig(
        symbol="MON",
        quote_asset="USD",
        max_leverage=3,
        min_order_size=10.0,
        tick_size=0.00001,
        display_name="MON",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
    PairConfig(
        symbol="LDO",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.001,
        display_name="Lido DAO",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
    PairConfig(
        symbol="CRV",
        quote_asset="USD",
        max_leverage=10,
        min_order_size=1.0,
        tick_size=0.0001,
        display_name="Curve",
        category=PairCategory.SMALL_CAP,
        whale_threshold_usd=2500,
    ),
]


# Helper functions
def get_all_pairs() -> List[PairConfig]:
    """Get all configured pairs"""
    return PAIRS


def get_active_pairs() -> List[PairConfig]:
    """Get only active pairs"""
    return [pair for pair in PAIRS if pair.is_active]


def get_pair_by_symbol(symbol: str) -> Optional[PairConfig]:
    """Get pair configuration by symbol"""
    symbol_upper = symbol.upper()
    return next((pair for pair in PAIRS if pair.symbol == symbol_upper), None)


def get_pairs_by_category(category: PairCategory) -> List[PairConfig]:
    """Get all pairs in a specific category"""
    return [pair for pair in PAIRS if pair.category == category]


def get_all_symbols() -> List[str]:
    """Get list of all symbol names"""
    return [pair.symbol for pair in PAIRS if pair.is_active]


def get_whale_threshold(symbol: str) -> float:
    """Get whale detection threshold for a symbol"""
    pair = get_pair_by_symbol(symbol)
    if pair and pair.whale_threshold_usd:
        return pair.whale_threshold_usd

    # Default threshold based on category
    if pair:
        category_defaults = {
            PairCategory.MAJOR: 25000,
            PairCategory.MID_CAP: 10000,
            PairCategory.EMERGING: 5000,
            PairCategory.SMALL_CAP: 2500,
        }
        return category_defaults.get(pair.category, 25000)

    return 25000  # Default fallback


def validate_symbol(symbol: str) -> bool:
    """Check if symbol is valid and active"""
    pair = get_pair_by_symbol(symbol)
    return pair is not None and pair.is_active


# Export counts for monitoring
PAIR_COUNTS = {
    "total": len(PAIRS),
    "major": len(get_pairs_by_category(PairCategory.MAJOR)),
    "mid_cap": len(get_pairs_by_category(PairCategory.MID_CAP)),
    "emerging": len(get_pairs_by_category(PairCategory.EMERGING)),
    "small_cap": len(get_pairs_by_category(PairCategory.SMALL_CAP)),
}
