# Changelog

All notable changes to the Nexwave trading strategy will be documented in this file.

## [Unreleased] - 2025-12-XX

### Fixed
- **Trading Engine Initialization:** Resolved `ImportError` in trading engine by correcting strategy class import names.
- **Redis Authentication:** Addressed Redis "Authentication required" errors by configuring `redis_password` in settings and updating `RedisClient` to use it for connections.
- **DB Writer Functionality:** Fixed `db-writer` service crashes by implementing missing Redis Stream (`xreadgroup`, `xgroup_create`, `xack`) methods in `RedisClient` and correcting message parsing to handle decoded responses.
- **Market Data WebSocket Connection:** Corrected WebSocket connection failure in `market-data` service by replacing `extra_headers` with `additional_headers` in the `websockets.connect` call.


## [2.1.0] - 2025-11-05

### Fixed - Order Placement System Now Operational

**Critical Fix**: Resolved order placement failures on Pacifica DEX
- Fixed signing format to match Pacifica API requirements
- Implemented recursive key sorting at all nested levels
- Changed to compact JSON formatting (no whitespace)
- Added `expiry_window` field to request structure
- Fixed order ID extraction from nested API response

**Testing Results**:
- ✅ Market orders successfully placing (Order IDs: 819975835, 819964926)
- ✅ Orders confirmed visible in Pacifica UI
- ⚠️ Limit orders returning 404 (endpoint investigation needed)

**Files Modified**:
- `src/nexwave/services/order_management/pacifica_client.py` - Complete signing overhaul
- `docs/ORDER_PLACEMENT_FIX.md` - Detailed fix documentation
- `ORDER_PLACEMENT_STATUS.md` - Updated with resolution
- `test_end_to_end.py` - New end-to-end testing script
- `test_order_debug.py` - New debugging utility

**Impact**:
- Order placement system now fully operational
- Trading engine can execute strategies in real mode
- End-to-end trading flow working: signal → order → execution
- System ready for live trading on Pacifica DEX

### Added
- **Order placement testing scripts**: Created test scripts for validating order placement
  - `scripts/test_order_placement.py` - Comprehensive test suite
  - `scripts/test_real_trading.py` - Real trading test with interactive prompts
  - `scripts/place_test_order.py` - Manual order placement utility
  - `scripts/quick_trading_test.py` - Quick connection test
- **Security documentation**: Added `SECURITY.md` with guidelines for handling sensitive data
- **Pacifica setup guide**: Added `PACIFICA_SETUP.md` with API configuration details
- **Order placement status**: Added `ORDER_PLACEMENT_STATUS.md` tracking current status

### Fixed
- **UUID validation**: Fixed `client_order_id` format validation (Pacifica requires valid UUID)
- **Timestamp in requests**: Added `timestamp` field to order request payloads
- **Agent wallet header**: Added `X-Agent-Wallet` header for API Agent Keys authentication
- **Private key handling**: Improved error handling for invalid key formats
- **Security**: Sanitized all error messages and logs to prevent exposing private keys
- **PyNaCl dependency**: Added PyNaCl to requirements for seed-to-keypair conversion support

### Changed
- **Order management service**: Enhanced error handling and validation
- **Pacifica client**: Improved keypair initialization with support for different key formats
- **Error logging**: All API errors now sanitized (status codes only, details at debug level)
- **Docker configuration**: Updated Dockerfile to include PyNaCl dependency

### Documentation
- Added comprehensive testing guide in `scripts/README.md`
- Documented security best practices
- Created troubleshooting guides for order placement

### Added
- **Short-side trading support**: Mean reversion strategy now trades both long and short positions
  - Short entry when price > mean + 2σ
  - Proper stop loss and take profit for short positions
- **Leverage integration**: Position sizing now uses leverage from pair configuration
  - Automatically applies pair-specific max leverage (capped at 5x for safety)
  - Improved capital efficiency for perpetual futures
- **Liquidation price calculation**: Added helper method to calculate liquidation prices
  - Supports both long and short positions
  - Configurable maintenance margin ratio

### Fixed
- **Portfolio value calculation**: Fixed hardcoded $100k value
  - Now calculates actual portfolio value: `initial_cash + unrealized_PnL + realized_PnL`
  - Critical for accurate risk management
- **Reduce-only orders**: Added `reduce_only=True` flag for all closing orders
  - Prevents accidentally opening new positions when closing existing ones
  - Critical safety feature for perpetual futures

### Changed
- **Mean reversion strategy**: Enhanced to support both directions
  - Entry thresholds: Long (price < mean - 2σ) and Short (price > mean + 2σ)
  - Exit logic handles both long and short positions correctly
- **Position sizing**: Now leverages pair configuration for dynamic leverage
  - Respects pair-specific max leverage limits
  - Applies leverage multiplier to position size calculations

### Documentation
- Added comprehensive trading strategy audit report (`TRADING_STRATEGY_AUDIT.md`)
- Documented all identified issues and recommended improvements
- Created implementation guide for future enhancements

