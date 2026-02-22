"""
Unit tests for momentum strategies
"""
import asyncio
import unittest
from unittest.mock import patch, MagicMock

from nexwave.strategies.momentum.long_term_momentum import LongTermMomentumStrategy
from nexwave.strategies.momentum.momentum_short import MomentumShortStrategy
from nexwave.strategies.momentum.short_term_momentum import ShortTermMomentumStrategy
from nexwave.strategies.base_strategy import SignalType

class TestShortTermMomentumStrategy(unittest.TestCase):

    def setUp(self):
        self.strategy = ShortTermMomentumStrategy(
            strategy_id="test_stm",
            symbol="BTC",
            portfolio_value=100000.0,
        )
        self.strategy.lookback_period = 5
        self.strategy.breakout_threshold = 1.02
        self.strategy.volume_multiplier = 1.2

    def _generate_mock_candles(self, price_trend, volume_trend):
        candles = []
        for i in range(10):
            candles.append({
                "open": 100 + i * price_trend,
                "high": 102 + i * price_trend,
                "low": 98 + i * price_trend,
                "close": 101 + i * price_trend,
                "volume": 1000 + i * volume_trend,
                "time": "2023-01-01T00:00:00Z"
            })
        return candles

    @patch('nexwave.strategies.momentum.short_term_momentum.get_candles')
    def test_buy_signal_on_breakout(self, mock_get_candles):
        # Arrange
        mock_candles = self._generate_mock_candles(1, 100)
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)

        market_data = {"price": 110} # Price breakout
        
        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertEqual(signal.symbol, "BTC")
        self.assertGreater(signal.amount, 0)


    @patch('nexwave.strategies.momentum.short_term_momentum.get_candles')
    def test_no_signal_when_no_breakout(self, mock_get_candles):
        # Arrange
        mock_candles = self._generate_mock_candles(1, 10)
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)
        
        market_data = {"price": 101} # No breakout

        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNone(signal)

class TestLongTermMomentumStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = LongTermMomentumStrategy(
            strategy_id="test_ltm",
            symbol="ETH",
            portfolio_value=100000.0,
        )
        self.strategy.lookback_period = 5
        self.strategy.trend_confirmation_period = 3

    def _generate_mock_candles(self, price_trend, high_increment, low_increment):
        candles = []
        for i in range(10):
            candles.append({
                "open": 100 + i * price_trend,
                "high": 102 + i * high_increment,
                "low": 98 + i * low_increment,
                "close": 101 + i * price_trend,
                "volume": 1000,
                "time": "2023-01-01T00:00:00Z"
            })
        return candles

    @patch('nexwave.strategies.momentum.long_term_momentum.get_candles')
    def test_buy_signal_on_uptrend(self, mock_get_candles):
        # Arrange
        mock_candles = self._generate_mock_candles(1, 2, 1) # higher highs and higher lows
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)

        market_data = {"price": 110}
        
        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.BUY)
        self.assertEqual(signal.symbol, "ETH")

    @patch('nexwave.strategies.momentum.long_term_momentum.get_candles')
    def test_no_signal_on_no_trend(self, mock_get_candles):
        # Arrange
        mock_candles = self._generate_mock_candles(0, 0, 0) # No trend
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)

        market_data = {"price": 101}
        
        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNone(signal)

class TestMomentumShortStrategy(unittest.TestCase):
    def setUp(self):
        self.strategy = MomentumShortStrategy(
            strategy_id="test_ms",
            symbol="SOL",
            portfolio_value=100000.0,
        )
        self.strategy.lookback_period = 5
        self.strategy.trend_confirmation_period = 3

    def _generate_mock_candles(self, price_trend, high_increment, low_increment):
        candles = []
        for i in range(10):
            candles.append({
                "open": 100 - i * price_trend,
                "high": 102 - i * high_increment,
                "low": 98 - i * low_increment,
                "close": 101 - i * price_trend,
                "volume": 1000,
                "time": "2023-01-01T00:00:00Z"
            })
        return candles

    @patch('nexwave.strategies.momentum.momentum_short.get_candles')
    def test_sell_signal_on_downtrend(self, mock_get_candles):
        # Arrange
        mock_candles = self._generate_mock_candles(1, 1, 2) # lower highs and lower lows
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)

        market_data = {"price": 90}
        
        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNotNone(signal)
        self.assertEqual(signal.signal_type, SignalType.SELL)
        self.assertEqual(signal.symbol, "SOL")

    @patch('nexwave.strategies.momentum.momentum_short.get_candles')
    def test_no_buy_signal(self, mock_get_candles):
        # This strategy should never generate a BUY signal
        # Arrange
        mock_candles = self._generate_mock_candles(-1, -1, -2) # uptrend
        mock_get_candles.return_value = asyncio.Future()
        mock_get_candles.return_value.set_result(mock_candles)

        market_data = {"price": 110}
        
        # Act
        signal = asyncio.run(self.strategy.generate_signal(market_data))

        # Assert
        self.assertIsNone(signal)

if __name__ == '__main__':
    unittest.main()
