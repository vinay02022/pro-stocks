"""
Quick API test script.
Run with: python test_api.py
"""

import asyncio
import os
import sys

# Set working directory
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))


async def test_api():
    """Test the data ingestion service via API."""
    print("\n" + "=" * 60)
    print("STOCKPRO - API TEST")
    print("=" * 60)

    from app.services.data_ingestion import get_data_ingestion_service
    from app.schemas.market import DataRequest, Timeframe

    service = get_data_ingestion_service()

    # Test 1: Health check
    print("\n[1] Testing Health Check...")
    print("-" * 40)
    is_healthy = await service.health_check()
    print(f"Service Healthy: {is_healthy}")

    # Test 2: Data sources status
    print("\n[2] Testing Data Sources Status...")
    print("-" * 40)
    status = await service.get_data_sources_status()
    for source, info in status.items():
        if isinstance(info, dict):
            available = info.get("available", "N/A")
            message = info.get("message", "N/A")
            print(f"{source}: {'OK' if available else 'UNAVAILABLE'} - {message}")

    # Test 3: Fetch market data
    print("\n[3] Testing Market Data Fetch...")
    print("-" * 40)

    request = DataRequest(
        symbols=["TATASTEEL", "RELIANCE"],
        timeframe=Timeframe.D1,
        lookback=10,
        include_options=False,
        include_news=False,
    )

    result = await service.execute(request)

    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings[:3]}..." if len(result.warnings) > 3 else f"Warnings: {result.warnings}")
    print(f"Data Source: {result.snapshot.metadata.source}")
    print(f"Latency: {result.snapshot.metadata.latency_ms}ms")

    for symbol_data in result.snapshot.symbols:
        print(f"\n{symbol_data.symbol}:")
        print(f"  Price: Rs.{symbol_data.current_price:.2f}")
        print(f"  Day Change: {symbol_data.day_change_percent:+.2f}%")
        print(f"  Candles: {len(symbol_data.ohlcv)}")
        if symbol_data.ohlcv:
            latest = symbol_data.ohlcv[-1]
            print(f"  Latest OHLC: O={latest.open:.2f} H={latest.high:.2f} L={latest.low:.2f} C={latest.close:.2f}")

    print("\n" + "=" * 60)
    print("API TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_api())
