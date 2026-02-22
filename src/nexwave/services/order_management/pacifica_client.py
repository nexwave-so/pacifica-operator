"""Pacifica DEX API client"""

import time
import json
import uuid
from typing import Dict, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import httpx
from solders.keypair import Keypair
from solders.message import Message
from solders.signature import Signature
import base58

from nexwave.common.config import settings
from nexwave.common.logger import logger
import math


class PacificaClient:
    """Client for interacting with Pacifica DEX API"""

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        private_key: Optional[str] = None,
        public_key: Optional[str] = None,
    ):
        self.api_url = api_url or settings.pacifica_api_url
        self.api_key = api_key or settings.pacifica_api_key
        # Agent Wallet: This is a Solana keypair generated specifically for API use
        # NOT the API key from the UI - that goes in PACIFICA_API_KEY
        self.private_key_str = private_key or settings.pacifica_agent_wallet_privkey
        self.public_key_str = public_key or settings.pacifica_agent_wallet_pubkey
        
        # Log API key status (but not the actual key)
        if self.api_key:
            logger.debug(f"API Key configured: {self.api_key[:10]}...")
        else:
            logger.warning("No API key configured. Some endpoints may require X-API-Key header.")

        # Initialize keypair
        self.keypair: Optional[Keypair] = None
        if self.private_key_str:
            if self.private_key_str == "your_agent_wallet_private_key" or not self.private_key_str.strip():
                logger.warning(
                    "Pacifica private key not properly configured. "
                    "Set PACIFICA_AGENT_WALLET_PRIVKEY environment variable."
                )
            else:
                try:
                    # Try to create keypair - handle different key formats
                    # Solana private keys can be:
                    # 1. Full base58 keypair (88 chars)
                    # 2. Base58 seed (32 bytes, ~44 chars) - need to convert
                    # 3. Hex seed (64 chars)
                    
                    # First try direct base58 string (full keypair format - ~88 chars)
                    try:
                        self.keypair = Keypair.from_base58_string(self.private_key_str)
                    except (ValueError, Exception) as e:
                        # If that fails, try treating it as a seed (32 bytes, ~44 base58 chars)
                        # This handles the case where user provides seed instead of full keypair
                        import base58
                        try:
                            # Decode the base58 string to get bytes
                            seed_bytes = base58.b58decode(self.private_key_str)
                            
                            # If it's 32 bytes, it's a seed - need to derive full keypair
                            if len(seed_bytes) == 32:
                                # Use Ed25519 to derive public key from private seed
                                # Solana uses Ed25519, so we need to generate the full keypair
                                from nacl.signing import SigningKey
                                from nacl.encoding import RawEncoder
                                
                                # Create signing key from seed
                                signing_key = SigningKey(seed_bytes, encoder=RawEncoder)
                                
                                # Get the verify key (public key)
                                verify_key = signing_key.verify_key
                                
                                # Solana keypair format: [private_key (32 bytes)][public_key (32 bytes)]
                                private_key_bytes = bytes(signing_key)
                                public_key_bytes = bytes(verify_key)
                                keypair_bytes = private_key_bytes + public_key_bytes
                                
                                # Create Solana keypair from 64-byte array
                                self.keypair = Keypair.from_bytes(keypair_bytes)
                            elif len(seed_bytes) == 64:
                                # Already a full keypair in bytes
                                self.keypair = Keypair.from_bytes(seed_bytes)
                            else:
                                raise ValueError(f"Invalid key format: decoded to {len(seed_bytes)} bytes, expected 32 (seed) or 64 (keypair)")
                        except ImportError:
                            # nacl not available, can't convert seed
                            raise ValueError(f"Invalid keypair format (too short for full keypair). If this is a seed, install PyNaCl. Error: {str(e)[:50]}")
                        except Exception as seed_error:
                            # Re-raise with helpful message
                            raise ValueError(f"Invalid keypair format. Tried keypair and seed formats. Error: {str(seed_error)[:50]}")
                    
                    logger.info(f"Initialized Pacifica client with wallet: {self.keypair.pubkey()}")
                except Exception as e:
                    # DO NOT log private key in error messages
                    error_msg = str(e)[:100]
                    logger.error(f"Failed to initialize keypair: {error_msg}")
                    logger.error("Check that PACIFICA_AGENT_WALLET_PRIVKEY is a valid Solana private key")
                    logger.error("Expected: base58-encoded keypair (~88 chars) or seed (32 bytes)")
                    # Don't raise here - allow paper trading to work without keypair
                    # Note: paper_trading check removed as it's not available in this context
        else:
            logger.warning("No private key provided. Real trading will not be available.")

    def sign_message(
        self, header: Dict[str, Any], payload: Dict[str, Any]
    ) -> tuple[str, str]:
        """
        Sign a message using the agent wallet

        According to Pacifica docs:
        1. Create message with signature header + data field
        2. Recursively sort all keys
        3. Create compact JSON (no whitespace)
        4. Sign with Ed25519
        5. Encode as base58

        Returns:
            Tuple of (message_string, signature_base58)
        """
        if not self.keypair:
            raise ValueError("Keypair not initialized")

        # Create message to sign - wrap payload in "data" field
        message_dict = {
            **header,
            "data": payload,
        }

        # Recursively sort all keys at all levels
        def sort_dict(d):
            if isinstance(d, dict):
                return {k: sort_dict(v) for k, v in sorted(d.items())}
            elif isinstance(d, list):
                return [sort_dict(item) for item in d]
            else:
                return d

        sorted_message = sort_dict(message_dict)

        # Create compact JSON (no whitespace)
        message_str = json.dumps(sorted_message, separators=(",", ":"))
        message_bytes = message_str.encode("utf-8")

        # Sign message
        signature = self.keypair.sign_message(message_bytes)
        signature_b58 = base58.b58encode(bytes(signature)).decode("utf-8")

        return message_str, signature_b58

    def get_tick_size(self, symbol: str) -> float:
        """
        Get tick size for a symbol. 
        Returns a reasonable default based on price range if not available.
        """
        # Common tick sizes by price range (fallback if API doesn't provide)
        # This is a heuristic - ideally fetch from Pacifica API symbol metadata
        symbol_upper = symbol.upper()
        
        # Known tick sizes from error messages (can be expanded)
        tick_size_map = {
            # High-value assets (BTC, ETH, etc.) - typically 0.01 or 1.0
            "BTC": 0.01,
            "ETH": 0.01,
            "SOL": 0.01,  # Added based on API error
            "BNB": 0.01,
            "ZEC": 0.01,
            "LTC": 0.01,
            "AAVE": 0.01,  # Added based on API error
            "PAXG": 0.01,
            "TAO": 0.01,
            # Mid-value assets - typically 0.0001 or 0.001
            "HYPE": 0.001,  # Added based on API error
            "LINK": 0.001,
            "UNI": 0.001,
            "AVAX": 0.001,
            "SUI": 0.001,
            # Low-value assets - typically 0.00001 or 0.0001
            "DOGE": 0.00001,  # Fixed: was 0.000001, API requires 0.00001
            "XRP": 0.00001,
            "ENA": 0.0001,
            "VIRTUAL": 0.0001,
            "FARTCOIN": 0.0001,
            "ASTER": 0.0001,
            "XPL": 0.0001,
            "MON": 0.00001,
            "PENGU": 0.00001,
            "WLFI": 0.00001,
            "LDO": 0.0001,
            "CRV": 0.0001,
            "2Z": 0.0001,
            "PUMP": 0.00001,
            # Very low-value assets - micro ticks
            "kPEPE": 0.000001,
            "KPEPE": 0.000001,
            "kBONK": 0.0001,  # Fixed based on API errors
            "KBONK": 0.0001,
        }
        
        if symbol_upper in tick_size_map:
            return tick_size_map[symbol_upper]
        
        # Default: use 0.0001 for most symbols (common for altcoins)
        # This is a fallback - should be fetched from API in production
        return 0.0001
    
    def round_to_tick_size(self, price: float, tick_size: float) -> float:
        """Round a price to the nearest valid tick size with proper precision handling"""
        if tick_size <= 0:
            return price

        # Calculate decimal places needed based on tick_size
        decimal_places = max(0, -int(math.floor(math.log10(tick_size))))

        # Use Decimal for exact precision to avoid floating point errors
        price_decimal = Decimal(str(price))
        tick_decimal = Decimal(str(tick_size))

        # Round to nearest tick size
        rounded = (price_decimal / tick_decimal).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_decimal

        # Convert back to float with proper precision
        return float(rounded.quantize(Decimal(10) ** -decimal_places))

    def get_lot_size(self, symbol: str) -> float:
        """Get the lot size (minimum amount increment) for a symbol"""
        # Map symbol to lot size (fetched from Pacifica API docs or testing)
        symbol_upper = symbol.upper()

        lot_size_map = {
            # Major pairs
            "BTC": 0.0001,
            "ETH": 0.001,
            "SOL": 0.01,

            # Mid-cap
            "HYPE": 0.1,
            "ZEC": 0.01,
            "BNB": 0.01,
            "XRP": 1.0,
            "PUMP": 1.0,  # Fixed: was 0.1, API requires 1.0
            "AAVE": 0.01,

            # Emerging
            "ENA": 0.1,
            "ASTER": 0.1,
            "KBONK": 0.1,  # kBONK
            "KPEPE": 0.1,  # kPEPE
            "LTC": 1.0,  # Fixed: was 0.01, API requires 1.0
            "PAXG": 0.001,
            "VIRTUAL": 0.1,
            "SUI": 0.1,
            "FARTCOIN": 0.1,
            "TAO": 0.01,
            "DOGE": 1.0,
            "XPL": 1.0,  # Fixed: was 0.1, API requires 1.0
            "AVAX": 0.1,
            "LINK": 0.1,
            "UNI": 1.0,  # Fixed: was 0.1, API requires 1.0
            "WLFI": 1.0,  # Fixed: was 0.1, API requires 1.0

            # Small-cap
            "PENGU": 1.0,
            "2Z": 0.1,
            "MON": 1.0,  # Fixed: was 0.1, API requires 1.0
            "LDO": 0.1,
            "CRV": 0.1,
        }

        if symbol_upper in lot_size_map:
            return lot_size_map[symbol_upper]

        # Default: 1.0 for most altcoins (safer default based on API errors)
        return 1.0

    def round_to_lot_size(self, amount: float, lot_size: float) -> float:
        """Round an amount to the nearest valid lot size"""
        if lot_size <= 0:
            return amount
        # Use floor to ensure we don't exceed available balance
        # Calculate decimal places needed based on lot_size
        decimal_places = max(0, -int(math.floor(math.log10(lot_size))))
        rounded = math.floor(amount / lot_size) * lot_size
        return round(rounded, decimal_places)

    def validate_tpsl(
        self, 
        symbol: str, 
        side: str, 
        entry_price: float, 
        stop_loss: Optional[float], 
        take_profit: Optional[float]
    ) -> tuple[Optional[float], Optional[float]]:
        """
        Validate and round TP/SL prices to valid tick sizes.
        Returns (validated_stop_loss, validated_take_profit) or (None, None) if invalid.
        """
        if stop_loss is None and take_profit is None:
            return None, None
        
        tick_size = self.get_tick_size(symbol)
        is_long = side.lower() == 'bid'
        
        validated_sl = None
        validated_tp = None
        
        # Validate and round stop loss
        if stop_loss is not None and stop_loss > 0:
            # For longs: SL must be below entry price
            # For shorts: SL must be above entry price
            if is_long:
                if stop_loss >= entry_price:
                    logger.warning(
                        f"{symbol}: Invalid stop loss for long position: "
                        f"SL={stop_loss} >= entry={entry_price}, setting to None"
                    )
                    validated_sl = None
                else:
                    validated_sl = self.round_to_tick_size(stop_loss, tick_size)
                    # Ensure it's still valid after rounding
                    if validated_sl >= entry_price:
                        # Round down one more tick
                        validated_sl = self.round_to_tick_size(entry_price - tick_size, tick_size)
            else:  # short
                if stop_loss <= entry_price:
                    logger.warning(
                        f"{symbol}: Invalid stop loss for short position: "
                        f"SL={stop_loss} <= entry={entry_price}, setting to None"
                    )
                    validated_sl = None
                else:
                    validated_sl = self.round_to_tick_size(stop_loss, tick_size)
                    # Ensure it's still valid after rounding
                    if validated_sl <= entry_price:
                        # Round up one more tick
                        validated_sl = self.round_to_tick_size(entry_price + tick_size, tick_size)
        
        # Validate and round take profit
        if take_profit is not None and take_profit > 0:
            # For longs: TP must be above entry price
            # For shorts: TP must be below entry price
            if is_long:
                if take_profit <= entry_price:
                    logger.warning(
                        f"{symbol}: Invalid take profit for long position: "
                        f"TP={take_profit} <= entry={entry_price}, setting to None"
                    )
                    validated_tp = None
                else:
                    validated_tp = self.round_to_tick_size(take_profit, tick_size)
                    # Ensure it's still valid after rounding
                    if validated_tp <= entry_price:
                        # Round up one more tick
                        validated_tp = self.round_to_tick_size(entry_price + tick_size, tick_size)
            else:  # short
                if take_profit >= entry_price:
                    logger.warning(
                        f"{symbol}: Invalid take profit for short position: "
                        f"TP={take_profit} >= entry={entry_price}, setting to None"
                    )
                    validated_tp = None
                else:
                    validated_tp = self.round_to_tick_size(take_profit, tick_size)
                    # Ensure it's still valid after rounding
                    if validated_tp >= entry_price:
                        # Round down one more tick
                        validated_tp = self.round_to_tick_size(entry_price - tick_size, tick_size)
        
        # Log validation results
        if validated_sl or validated_tp:
            logger.debug(
                f"{symbol} TP/SL validation: entry={entry_price}, "
                f"SL={validated_sl} (was {stop_loss}), TP={validated_tp} (was {take_profit}), "
                f"tick_size={tick_size}"
            )
        
        return validated_sl, validated_tp

    def create_signature_header(
        self, order_type: str = "create_market_order", expiry_window_ms: int = 5000
    ) -> Dict[str, Any]:
        """Create signature header for order"""

        return {
            "timestamp": int(time.time() * 1000),
            "expiry_window": expiry_window_ms,
            "type": order_type,
        }

    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        reduce_only: bool = False,
        slippage_percent: float = 0.5,
        client_order_id: Optional[str] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        entry_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a market order on Pacifica with optional TP/SL"""

        if not self.keypair:
            raise ValueError("Keypair not initialized for order creation")

        # Pacifica requires client_order_id to be a valid UUID format
        if client_order_id:
            # If provided, ensure it's a valid UUID format
            try:
                # Try to parse as UUID to validate format
                uuid.UUID(client_order_id)
            except (ValueError, TypeError):
                # If not valid UUID, generate a new one and log warning
                logger.warning(f"Invalid client_order_id format '{client_order_id}', generating new UUID")
                client_order_id = str(uuid.uuid4())
        else:
            client_order_id = str(uuid.uuid4())

        # Create signature header
        header = self.create_signature_header()

        # Round amount to lot size to comply with Pacifica requirements
        lot_size = self.get_lot_size(symbol)
        rounded_amount = self.round_to_lot_size(amount, lot_size)

        # Log if amount was adjusted
        if rounded_amount != amount:
            logger.debug(
                f"{symbol}: Amount rounded from {amount:.6f} to {rounded_amount:.6f} "
                f"(lot_size={lot_size})"
            )

        # Create payload
        payload = {
            "symbol": symbol.upper(),
            "side": side.lower(),  # 'bid' or 'ask'
            "amount": str(rounded_amount),
            "reduce_only": reduce_only,
            "slippage_percent": str(slippage_percent),
            "client_order_id": client_order_id,
        }

        # Validate and round TP/SL if provided
        validated_sl = None
        validated_tp = None
        if (stop_loss is not None and stop_loss > 0) or (take_profit is not None and take_profit > 0):
            if entry_price is None:
                logger.warning(
                    f"{symbol}: TP/SL provided but entry_price not specified. "
                    f"Using TP/SL values as-is (may fail tick size validation)"
                )
                # Use provided values but round to tick size
                tick_size = self.get_tick_size(symbol)
                if stop_loss and stop_loss > 0:
                    validated_sl = self.round_to_tick_size(stop_loss, tick_size)
                if take_profit and take_profit > 0:
                    validated_tp = self.round_to_tick_size(take_profit, tick_size)
            else:
                validated_sl, validated_tp = self.validate_tpsl(
                    symbol, side, entry_price, stop_loss, take_profit
                )

        # Add stop loss if validated
        if validated_sl is not None and validated_sl > 0:
            # For stop loss, use stop-market orders (limit_price slightly worse than stop_price)
            slippage = 0.001  # 0.1% slippage
            if side.lower() == 'bid':
                # Long position: stop loss sells, so limit price is below stop price
                limit_price = validated_sl * (1 - slippage)
            else:
                # Short position: stop loss buys, so limit price is above stop price
                limit_price = validated_sl * (1 + slippage)

            tick_size = self.get_tick_size(symbol)
            limit_price = self.round_to_tick_size(limit_price, tick_size)

            payload["stop_loss"] = {
                "stop_price": str(validated_sl),
                "limit_price": str(limit_price),
            }

        # Add take profit if validated
        if validated_tp is not None and validated_tp > 0:
            # For take profit, use stop-limit orders (limit_price slightly worse than stop_price)
            slippage = 0.001  # 0.1% slippage
            if side.lower() == 'bid':
                # Long position: take profit sells, so limit price is below stop price
                limit_price = validated_tp * (1 - slippage)
            else:
                # Short position: take profit buys, so limit price is above stop price
                limit_price = validated_tp * (1 + slippage)

            tick_size = self.get_tick_size(symbol)
            limit_price = self.round_to_tick_size(limit_price, tick_size)

            payload["take_profit"] = {
                "stop_price": str(validated_tp),
                "limit_price": str(limit_price),
            }
        
        # Log whether TP/SL is included (for debugging)
        if validated_sl is None and validated_tp is None:
            logger.debug(f"Creating order without TP/SL for {symbol}")
        elif validated_sl is None or validated_tp is None:
            logger.debug(f"Creating order with partial TP/SL for {symbol}: SL={validated_sl}, TP={validated_tp}")
        else:
            logger.debug(f"Creating order with TP/SL for {symbol}: SL={validated_sl}, TP={validated_tp}")

        # Sign message
        message_str, signature = self.sign_message(header, payload)

        # Prepare request - include auth fields + original payload (not wrapped)
        request_data = {
            "account": str(self.keypair.pubkey()),
            "signature": signature,
            "timestamp": header["timestamp"],
            "expiry_window": header["expiry_window"],
            **payload,  # Original payload, not wrapped in "data"
        }

        # Submit to Pacifica API
        url = f"{self.api_url}/orders/create_market"

        # Prepare headers
        headers = {
            "X-Agent-Wallet": str(self.keypair.pubkey()),  # Required for API Agent Keys
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=request_data, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    # Pacifica API returns nested structure: {"success": true, "data": {"order_id": ...}}
                    order_id = result.get('data', {}).get('order_id') if isinstance(result.get('data'), dict) else result.get('order_id')
                    logger.info(
                        f"Market order created: {symbol} {side} {amount} "
                        f"(order_id={order_id})"
                    )
                    return result
                else:
                    # Don't log full response text as it might contain sensitive data
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    # Log sanitized error (first 200 chars only, no sensitive data)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except httpx.TimeoutException:
            error_msg = "Pacifica API timeout"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error creating market order: {e}")
            raise

    async def create_limit_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        reduce_only: bool = False,
        client_order_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a limit order on Pacifica"""

        if not self.keypair:
            raise ValueError("Keypair not initialized for order creation")

        # Pacifica requires client_order_id to be a valid UUID format
        if client_order_id:
            try:
                uuid.UUID(client_order_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid client_order_id format '{client_order_id}', generating new UUID")
                client_order_id = str(uuid.uuid4())
        else:
            client_order_id = str(uuid.uuid4())

        # Create signature header
        header = self.create_signature_header(order_type="create_limit_order")

        # Create payload
        payload = {
            "symbol": symbol.upper(),
            "side": side.lower(),
            "amount": str(amount),
            "price": str(price),
            "reduce_only": reduce_only,
            "client_order_id": client_order_id,
        }

        # Sign message
        message_str, signature = self.sign_message(header, payload)

        # Prepare request - include auth fields + original payload (not wrapped)
        request_data = {
            "account": str(self.keypair.pubkey()),
            "signature": signature,
            "timestamp": header["timestamp"],
            "expiry_window": header["expiry_window"],
            **payload,  # Original payload, not wrapped in "data"
        }

        # Submit to Pacifica API
        url = f"{self.api_url}/orders/create_limit"

        # Prepare headers
        headers = {
            "X-Agent-Wallet": str(self.keypair.pubkey()),  # Required for API Agent Keys
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=request_data, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    # Pacifica API returns nested structure: {"success": true, "data": {"order_id": ...}}
                    order_id = result.get('data', {}).get('order_id') if isinstance(result.get('data'), dict) else result.get('order_id')
                    logger.info(
                        f"Limit order created: {symbol} {side} {amount} @ {price} "
                        f"(order_id={order_id})"
                    )
                    return result
                else:
                    # Don't log full response text as it might contain sensitive data
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    # Log sanitized error (first 200 chars only, no sensitive data)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except httpx.TimeoutException:
            error_msg = "Pacifica API timeout"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error creating limit order: {e}")
            raise

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order on Pacifica"""

        if not self.keypair:
            raise ValueError("Keypair not initialized")

        # Create signature header
        header = self.create_signature_header(order_type="cancel_order")

        # Create payload
        payload = {
            "order_id": order_id,
        }

        # Sign message
        message_str, signature = self.sign_message(header, payload)

        # Prepare request
        request_data = {
            "account": str(self.keypair.pubkey()),
            "signature": signature,
            **payload,
        }

        # Submit to Pacifica API
        url = f"{self.api_url}/orders/cancel"

        # Prepare headers
        headers = {
            "X-Agent-Wallet": str(self.keypair.pubkey()),  # Required for API Agent Keys
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=request_data, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Order canceled: {order_id}")
                    return result
                else:
                    # Don't log full response text as it might contain sensitive data
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    # Log sanitized error (first 200 chars only, no sensitive data)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except httpx.TimeoutException:
            error_msg = "Pacifica API timeout"
            logger.error(error_msg)
            raise Exception(error_msg)
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            raise

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get order status from Pacifica"""

        url = f"{self.api_url}/orders/{order_id}"

        # Prepare headers
        headers = {
            "X-Agent-Wallet": str(self.keypair.pubkey()),  # Required for API Agent Keys
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    # Don't log full response text as it might contain sensitive data
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    # Log sanitized error (first 200 chars only, no sensitive data)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error getting order status: {e}")
            raise

    async def get_positions(self) -> list[Dict[str, Any]]:
        """Get current positions from Pacifica"""

        if not self.keypair:
            raise ValueError("Keypair not initialized")

        # Prepare request - GET with account as query parameter
        account = str(self.keypair.pubkey())
        url = f"{self.api_url}/positions?account={account}"

        # Prepare headers
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    # Don't log full response text as it might contain sensitive data
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    # Log sanitized error (first 200 chars only, no sensitive data)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    async def set_position_tpsl(
        self,
        symbol: str,
        side: str,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Set stop loss and take profit for an existing position"""

        if not self.keypair:
            raise ValueError("Keypair not initialized")

        if not stop_loss and not take_profit:
            raise ValueError("At least one of stop_loss or take_profit must be provided")

        # Prepare header for signature
        header = {
            "operation": "set_position_tpsl",
            "timestamp": int(time.time() * 1000),
            "expiry_window": 60000,  # 60 seconds
        }

        # Prepare payload
        payload = {
            "symbol": symbol.upper(),
            "side": side.lower(),  # 'bid' or 'ask'
        }

        # Add stop loss if provided
        if stop_loss:
            # For stop loss, use stop-market orders (limit_price slightly worse than stop_price)
            slippage = 0.001  # 0.1% slippage
            if side == 'bid':
                # Long position: stop loss sells, so limit price is below stop price
                limit_price = stop_loss * (1 - slippage)
            else:
                # Short position: stop loss buys, so limit price is above stop price
                limit_price = stop_loss * (1 + slippage)

            payload["stop_loss"] = {
                "stop_price": str(stop_loss),
                "limit_price": str(round(limit_price, 6)),
            }

        # Add take profit if provided
        if take_profit:
            # For take profit, use stop-limit orders (limit_price slightly worse than stop_price)
            slippage = 0.001  # 0.1% slippage
            if side == 'bid':
                # Long position: take profit sells, so limit price is below stop price
                limit_price = take_profit * (1 - slippage)
            else:
                # Short position: take profit buys, so limit price is above stop price
                limit_price = take_profit * (1 + slippage)

            payload["take_profit"] = {
                "stop_price": str(take_profit),
                "limit_price": str(round(limit_price, 6)),
            }

        # Sign message
        message_str, signature = self.sign_message(header, payload)

        # Prepare request
        request_data = {
            "account": str(self.keypair.pubkey()),
            "signature": signature,
            "timestamp": header["timestamp"],
            "expiry_window": header["expiry_window"],
            "agent_wallet": str(self.keypair.pubkey()),  # Required for agent keys
            **payload,
        }

        # Submit to Pacifica API
        url = f"{self.api_url}/positions/tpsl"

        # Prepare headers
        headers = {
            "X-Agent-Wallet": str(self.keypair.pubkey()),  # Required for API Agent Keys
        }
        if self.api_key:
            headers["X-API-Key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=request_data, headers=headers)

                if response.status_code == 200:
                    result = response.json()
                    logger.info(
                        f"TP/SL set for {symbol} {side}: "
                        f"SL={stop_loss}, TP={take_profit}"
                    )
                    return result
                else:
                    error_msg = f"Pacifica API error: {response.status_code}"
                    logger.error(error_msg)
                    error_text = response.text[:200] if response.text else "No error details"
                    logger.debug(f"API error details: {error_text}")
                    raise Exception(error_msg)

        except Exception as e:
            logger.error(f"Error setting TP/SL: {e}")
            raise

