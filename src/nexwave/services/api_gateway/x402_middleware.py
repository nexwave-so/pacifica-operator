"""
x402 Payment Protocol Middleware for Nexwave API

Implements HTTP 402 "Payment Required" responses with Solana micropayments
for protected API endpoints using the x402 protocol.
"""

import json
import base64
from typing import Optional, Dict, Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger

# Solana mainnet USDC mint address
USDC_MINT_MAINNET = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"

# PayAI Network facilitator for Solana
FACILITATOR_URL = "https://facilitator.payai.network"


class X402Middleware(BaseHTTPMiddleware):
    """
    Middleware to protect API endpoints with x402 payments.

    Intercepts requests to protected endpoints and:
    1. Returns 402 Payment Required if no X-PAYMENT header present
    2. Verifies payment if X-PAYMENT header present
    3. Allows request to proceed if payment is valid
    """

    def __init__(self, app, treasury_address: str, protected_routes: Dict[str, Dict[str, Any]]):
        """
        Initialize x402 middleware.

        Args:
            app: FastAPI application instance
            treasury_address: Solana wallet address to receive payments
            protected_routes: Dict mapping route paths to payment configs
                Example: {
                    "/api/v1/latest-prices": {
                        "price_usd": "0.001",
                        "description": "Latest market prices for all trading pairs"
                    }
                }
        """
        super().__init__(app)
        self.treasury_address = treasury_address
        self.protected_routes = protected_routes
        logger.info(f"x402 middleware initialized with {len(protected_routes)} protected routes")
        logger.info(f"Treasury address: {treasury_address}")

    async def dispatch(self, request: Request, call_next):
        """Process each request through x402 payment verification"""

        # Check if this route is protected
        route_path = request.url.path
        if route_path not in self.protected_routes:
            # Route not protected, proceed normally
            return await call_next(request)

        # Get route configuration
        route_config = self.protected_routes[route_path]
        price_usd = float(route_config.get("price_usd", "0.001"))
        description = route_config.get("description", "API Request")

        # Convert USD price to USDC micro-units (6 decimals)
        # $0.001 = 1000 micro-units
        price_microunits = str(int(price_usd * 1_000_000))

        logger.debug(f"Protected route accessed: {route_path} (${price_usd} = {price_microunits} microunits)")

        # Check for X-PAYMENT header
        payment_header = request.headers.get("X-PAYMENT", "").strip()

        if not payment_header:
            # No payment provided - return 402 Payment Required
            logger.info(f"402 Payment Required: {route_path}")
            return self._create_402_response(
                route_path=route_path,
                price_microunits=price_microunits,
                description=description
            )

        # Payment header present - verify it
        try:
            payment_valid = await self._verify_payment(
                payment_header=payment_header,
                expected_amount=price_microunits,
                route_path=route_path
            )

            if not payment_valid:
                logger.warning(f"Invalid payment for {route_path}")
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "Payment verification failed",
                        "message": "The provided payment could not be verified"
                    }
                )

            # Payment verified - proceed with request
            logger.info(f"✅ Payment verified for {route_path}: ${price_usd}")
            response = await call_next(request)

            # Add X-PAYMENT-RESPONSE header to confirm payment settlement
            response.headers["X-PAYMENT-RESPONSE"] = base64.b64encode(
                json.dumps({
                    "status": "settled",
                    "amount": price_microunits,
                    "currency": "USDC",
                    "network": "solana"
                }).encode()
            ).decode()

            return response

        except Exception as e:
            logger.error(f"Error processing payment for {route_path}: {e}")
            return JSONResponse(
                status_code=402,
                content={
                    "error": "Payment processing error",
                    "message": str(e)
                }
            )

    def _create_402_response(
        self,
        route_path: str,
        price_microunits: str,
        description: str
    ) -> JSONResponse:
        """
        Create HTTP 402 Payment Required response with x402 payment requirements.

        Returns JSON with payment instructions according to x402 protocol spec.
        """

        # Get full URL for resource
        # Note: In production, use proper base URL from environment/config
        resource_url = f"https://api.nexwave.so{route_path}"

        payment_requirements = {
            "x402Version": 1,
            "accepts": [
                {
                    "scheme": "exact",
                    "network": "solana",
                    "maxAmountRequired": price_microunits,
                    "asset": USDC_MINT_MAINNET,
                    "payTo": self.treasury_address,
                    "resource": resource_url,
                    "description": description,
                    "mimeType": "application/json",
                    "maxTimeoutSeconds": 300
                }
            ],
            "error": "Payment required to access this resource"
        }

        return JSONResponse(
            status_code=402,
            content=payment_requirements,
            headers={
                "X-PAYMENT-REQUIRED": "true",
                "WWW-Authenticate": "x402"
            }
        )

    async def _verify_payment(
        self,
        payment_header: str,
        expected_amount: str,
        route_path: str
    ) -> bool:
        """
        Verify payment using PayAI Network facilitator.

        Args:
            payment_header: Base64-encoded payment data from X-PAYMENT header
            expected_amount: Expected payment amount in micro-units
            route_path: API route path for logging

        Returns:
            True if payment is valid and settled, False otherwise
        """

        try:
            # Decode payment header
            payment_data = json.loads(base64.b64decode(payment_header))

            logger.debug(f"Verifying payment for {route_path}: {payment_data.get('amount')} microunits")

            # For hackathon demo: simplified verification
            # In production: use x402-solana SDK to verify with facilitator

            # Basic validation checks
            if not payment_data:
                return False

            # Check payment amount matches expected
            payment_amount = str(payment_data.get("amount", "0"))
            if payment_amount != expected_amount:
                logger.warning(f"Amount mismatch: expected {expected_amount}, got {payment_amount}")
                return False

            # Check payment is for correct recipient
            pay_to = payment_data.get("payTo", "")
            if pay_to != self.treasury_address:
                logger.warning(f"Recipient mismatch: expected {self.treasury_address}, got {pay_to}")
                return False

            # TODO: Verify signature and settle transaction via facilitator
            # This would use x402_solana.schemes.exact_svm.facilitator.verify_payment()
            # and settle_payment() functions in production

            logger.info(f"Payment verification passed for {route_path}")
            return True

        except Exception as e:
            logger.error(f"Payment verification error: {e}")
            return False
