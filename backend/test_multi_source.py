"""
Test script for multi-source data integration.
Run with: python test_multi_source.py
"""

import asyncio
import os
import sys

# Set working directory to backend folder
backend_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(backend_dir)

# Add parent directory to path
sys.path.insert(0, backend_dir)

# Load environment variables from .env
from dotenv import load_dotenv
load_dotenv(os.path.join(backend_dir, ".env"))


async def test_data_sources():
    """Test all data source connections."""
    print("\n" + "=" * 60)
    print("STOCKPRO - MULTI-SOURCE DATA TEST")
    print("=" * 60)

    from app.services.data_ingestion.multi_source import (
        validate_data_sources,
        fetch_multi_source_data,
        get_cross_validated_quote,
    )
    from app.schemas.market import Timeframe

    # Test 1: Check data source connectivity
    print("\n[1] Testing Data Source Connectivity...")
    print("-" * 40)

    try:
        status = await validate_data_sources()

        print(f"Yahoo Finance: {'OK' if status.get('yahoo_finance', {}).get('available') else 'UNAVAILABLE'}")
        print(f"  Message: {status.get('yahoo_finance', {}).get('message', 'N/A')}")

        print(f"\nAngel One:     {'OK' if status.get('angel_one', {}).get('available') else 'UNAVAILABLE'}")
        print(f"  Message: {status.get('angel_one', {}).get('message', 'N/A')}")

        overall = status.get("overall", {})
        print(f"\nOverall Status:")
        print(f"  Sources Available: {overall.get('sources_available', 0)}")
        print(f"  Primary Source: {overall.get('primary_source', 'N/A')}")
        print(f"  Recommendation: {overall.get('recommendation', 'N/A')}")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

    # Test 2: Fetch multi-source data for test symbols
    print("\n\n[2] Testing Multi-Source Data Fetch...")
    print("-" * 40)

    test_symbols = ["TATASTEEL", "RELIANCE", "INFY"]

    for symbol in test_symbols:
        print(f"\n{symbol}:")
        try:
            data = await fetch_multi_source_data(
                symbol=symbol,
                timeframe=Timeframe.D1,
                lookback=10,
            )

            if data:
                print(f"  Price: Rs.{data.primary_data.current_price:.2f}")
                print(f"  Day Change: {data.primary_data.day_change_percent:+.2f}%")
                print(f"  Sources: {', '.join(data.sources_used)}")
                print(f"  Quality Metrics:")
                print(f"    - Confidence: {data.quality.confidence:.0%}")
                print(f"    - Source Count: {data.quality.source_count}")
                print(f"    - Price Match: {'Yes' if data.quality.price_match else 'No'}")
                print(f"    - Data Freshness: {data.quality.data_freshness}")
                if data.quality.warnings:
                    print(f"    - Warnings: {data.quality.warnings}")
            else:
                print("  No data available")

        except Exception as e:
            print(f"  ERROR: {e}")

    # Test 3: Cross-validated quote
    print("\n\n[3] Testing Cross-Validated Quote...")
    print("-" * 40)

    for symbol in ["TATASTEEL", "NIFTY"]:
        print(f"\n{symbol}:")
        try:
            quote = await get_cross_validated_quote(symbol)
            if quote:
                print(f"  Price: Rs.{quote['price']:.2f}")
                print(f"  Sources: {', '.join(quote['sources'])}")
                print(f"  Confidence: {quote['confidence']:.0%}")
                if quote['source_count'] >= 2:
                    print(f"  Price Match: {'Yes' if quote['price_match'] else 'No'}")
                    print(f"  Max Deviation: {quote['max_deviation_percent']:.4f}%")
            else:
                print("  No quote available")
        except Exception as e:
            print(f"  ERROR: {e}")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_data_sources())
