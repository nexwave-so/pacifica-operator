"""
Nexwave: Autonomous Trading Agent for Pacifica Perpetual DEX

Main entry point - run individual services via their modules:
- Market Data: python -m src.nexwave.services.market_data.client
- DB Writer: python -m src.nexwave.services.db_writer.service
- API Gateway: python -m src.nexwave.services.api_gateway.main

Or use Docker Compose: docker-compose up
"""

def main():
    print("Nexwave: Autonomous Trading Agent for Pacifica")
    print("\nTo run services:")
    print("  Market Data Service: python -m src.nexwave.services.market_data.client")
    print("  Database Writer: python -m src.nexwave.services.db_writer.service")
    print("  API Gateway: python -m src.nexwave.services.api_gateway.main")
    print("\nOr use Docker Compose: docker-compose up")


if __name__ == "__main__":
    main()
