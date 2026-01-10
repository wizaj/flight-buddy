#!/usr/bin/env python3
"""Quick test to verify API connection."""

import sys
from datetime import date, timedelta

from flight_buddy.client import AmadeusClient, AmadeusError
from flight_buddy.models import parse_flight_offers, parse_flight_schedule


def main():
    print("🔌 Testing Amadeus API connection...\n")
    
    try:
        client = AmadeusClient()
        print("✅ Client initialized")
        
        # Test auth
        token = client._auth.get_token()
        print(f"✅ Auth successful (token: {token[:20]}...)")
        
        # Test flight search
        test_date = (date.today() + timedelta(days=30)).isoformat()
        print(f"\n📍 Testing flight search: SYD → BKK on {test_date}")
        
        response = client.search_flights(
            origin="SYD",
            destination="BKK",
            departure_date=test_date,
            max_results=3,
        )
        
        offers = parse_flight_offers(response)
        print(f"✅ Search returned {len(offers)} offers")
        
        if offers:
            offer = offers[0]
            print(f"   First offer: {offer.price} - {offer.outbound.segments[0].flight_code}")
        
        # Test flight schedule (if sandbox supports it)
        print(f"\n📍 Testing flight schedule: BA986 on {test_date}")
        try:
            response = client.get_flight_schedule(
                carrier_code="BA",
                flight_number="986",
                departure_date=test_date,
            )
            schedules = parse_flight_schedule(response)
            print(f"✅ Schedule returned {len(schedules)} flights")
            if schedules:
                s = schedules[0]
                print(f"   {s.flight_code}: {s.departure.code} → {s.arrival.code}")
        except AmadeusError as e:
            print(f"⚠️  Schedule lookup not available in sandbox: {e}")
        
        print("\n🎉 All tests passed!")
        return 0
        
    except AmadeusError as e:
        print(f"\n❌ API Error: {e}")
        if e.details:
            for d in e.details:
                print(f"   {d.get('title')}: {d.get('detail')}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
