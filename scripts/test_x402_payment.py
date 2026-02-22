#!/usr/bin/env python3
"""
x402 Payment Flow Demo Script for Nexwave API

This script demonstrates the complete x402 payment protocol flow:
1. Request protected endpoint without payment → Receive 402 Payment Required
2. Parse payment requirements
3. Create and sign Solana USDC payment transaction
4. Retry request with X-PAYMENT header → Receive 200 OK with data

Requirements:
- Test wallet funded with SOL (for transaction fees) and USDC (for payment)
- Solana mainnet connection
"""

import json
import base64
import httpx
import asyncio
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.system_program import TransferParams, transfer
from solders.transaction import Transaction
from solders.message import Message
from solders.hash import Hash
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
import base58

# Configuration
API_BASE_URL = "http://localhost:8000"
ENDPOINT = "/api/v1/latest-prices"
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# Test wallet (generated - REPLACE WITH YOUR FUNDED WALLET)
TEST_WALLET_PRIVATE_KEY = "your_test_wallet_private_key_here"

# USDC mainnet mint address
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"


class Colors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


async def step1_request_without_payment():
    """Step 1: Request protected endpoint without payment"""
    print_header("STEP 1: Request Protected Endpoint (No Payment)")

    print_info(f"Requesting: {API_BASE_URL}{ENDPOINT}")
    print_info("X-PAYMENT header: [NOT PROVIDED]")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}{ENDPOINT}")

        print(f"\nStatus Code: {Colors.WARNING}{response.status_code}{Colors.ENDC}")

        if response.status_code == 402:
            print_success("Received HTTP 402 Payment Required")

            payment_requirements = response.json()
            print(f"\n{Colors.BOLD}Payment Requirements:{Colors.ENDC}")
            print(json.dumps(payment_requirements, indent=2))

            return payment_requirements
        else:
            print_error(f"Unexpected status code: {response.status_code}")
            return None


async def step2_parse_payment_requirements(payment_requirements):
    """Step 2: Parse payment requirements"""
    print_header("STEP 2: Parse Payment Requirements")

    if not payment_requirements or "accepts" not in payment_requirements:
        print_error("No payment requirements found")
        return None

    req = payment_requirements["accepts"][0]

    print_info(f"Network: {req['network']}")
    print_info(f"Amount: {req['maxAmountRequired']} micro-units")
    print_info(f"Amount (USD): ${int(req['maxAmountRequired']) / 1_000_000:.6f}")
    print_info(f"Asset: {req['asset']}")
    print_info(f"Pay To: {req['payTo']}")
    print_info(f"Description: {req['description']}")

    return req


async def step3_create_payment(payment_req):
    """Step 3: Create payment transaction (demo/simplified)"""
    print_header("STEP 3: Create Payment Transaction")

    print_warning("NOTE: This is a DEMO implementation for hackathon")
    print_warning("Production requires actual SPL token transfer transaction")

    # Load test wallet
    try:
        keypair = Keypair.from_base58_string(TEST_WALLET_PRIVATE_KEY)
        print_success(f"Loaded wallet: {keypair.pubkey()}")
    except Exception as e:
        print_error(f"Failed to load wallet: {e}")
        return None

    # For hackathon demo: create mock payment data
    # In production: create actual SPL token transfer transaction
    payment_data = {
        "version": 1,
        "network": "solana",
        "amount": payment_req["maxAmountRequired"],
        "asset": payment_req["asset"],
        "payTo": payment_req["payTo"],
        "from": str(keypair.pubkey()),
        "timestamp": int(asyncio.get_event_loop().time()),
        "signature": "demo_signature_for_hackathon"
    }

    print_info("Payment data created:")
    print(json.dumps(payment_data, indent=2))

    # Encode payment as base64 for X-PAYMENT header
    payment_json = json.dumps(payment_data)
    payment_b64 = base64.b64encode(payment_json.encode()).decode()

    print_success(f"Payment encoded (length: {len(payment_b64)} bytes)")

    return payment_b64


async def step4_request_with_payment(payment_header):
    """Step 4: Retry request with payment"""
    print_header("STEP 4: Retry Request with Payment")

    print_info(f"Requesting: {API_BASE_URL}{ENDPOINT}")
    print_info(f"X-PAYMENT header: [PROVIDED - {len(payment_header)} bytes]")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{API_BASE_URL}{ENDPOINT}",
            headers={"X-PAYMENT": payment_header}
        )

        print(f"\nStatus Code: {Colors.OKGREEN if response.status_code == 200 else Colors.FAIL}{response.status_code}{Colors.ENDC}")

        if response.status_code == 200:
            print_success("Payment verified! Access granted.")

            # Check for payment response header
            payment_response = response.headers.get("X-PAYMENT-RESPONSE")
            if payment_response:
                print(f"\n{Colors.BOLD}Payment Response Header:{Colors.ENDC}")
                decoded = json.loads(base64.b64decode(payment_response))
                print(json.dumps(decoded, indent=2))

            # Show data snippet
            data = response.json()
            print(f"\n{Colors.BOLD}Response Data (first 3 prices):{Colors.ENDC}")
            for price in data.get("prices", [])[:3]:
                symbol = price.get("symbol")
                price_val = price.get("price")
                change = price.get("change_24h_pct", 0)
                change_color = Colors.OKGREEN if change > 0 else Colors.FAIL
                print(f"  {symbol}: ${price_val:.6f} ({change_color}{change:+.2f}%{Colors.ENDC})")

            print_info(f"Total pairs: {data.get('count', 0)}")

            return data
        else:
            print_error("Payment verification failed")
            print(response.text)
            return None


async def main():
    """Run complete x402 payment flow demo"""
    print(f"""
{Colors.BOLD}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           Nexwave x402 Payment Flow Demo Script              ║
║                                                               ║
║    Demonstrating HTTP 402 Payment Required on Solana         ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.ENDC}
""")

    try:
        # Step 1: Request without payment (expect 402)
        payment_requirements = await step1_request_without_payment()
        if not payment_requirements:
            return

        input(f"\n{Colors.OKCYAN}Press Enter to continue to Step 2...{Colors.ENDC}")

        # Step 2: Parse payment requirements
        payment_req = await step2_parse_payment_requirements(payment_requirements)
        if not payment_req:
            return

        input(f"\n{Colors.OKCYAN}Press Enter to continue to Step 3...{Colors.ENDC}")

        # Step 3: Create payment
        payment_header = await step3_create_payment(payment_req)
        if not payment_header:
            return

        input(f"\n{Colors.OKCYAN}Press Enter to continue to Step 4...{Colors.ENDC}")

        # Step 4: Request with payment (expect 200)
        data = await step4_request_with_payment(payment_header)

        print_header("DEMO COMPLETE")

        if data:
            print_success("Successfully demonstrated x402 payment protocol!")
            print_info("Status: 402 → Payment → 200 OK")
        else:
            print_warning("Payment verification pending (demo mode)")
            print_info("For production: implement actual SPL token transfer")

        print(f"\n{Colors.BOLD}Next Steps:{Colors.ENDC}")
        print("1. Fund test wallet with SOL and USDC")
        print("2. Implement real SPL token transfer (see Solana docs)")
        print("3. Verify transaction on Solana Explorer")
        print("4. Deploy to production with real facilitator")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.WARNING}Demo interrupted by user{Colors.ENDC}")
    except Exception as e:
        print_error(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
