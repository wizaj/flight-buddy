# SerpApi Google Flights Provider

## Overview

SerpApi scrapes Google Flights and returns structured JSON. Read-only (search/display, no booking).

**Docs:** https://serpapi.com/google-flights-api

## Auth

Simple API key in query params:
```
GET https://serpapi.com/search?engine=google_flights&api_key=XXX&...
```

Env var: `SERPAPI_API_KEY`

## API Mapping

### search_flights() → GET /search

| Flight Buddy Param | SerpApi Param | Notes |
|-------------------|---------------|-------|
| origin | departure_id | IATA code (e.g., JNB) |
| destination | arrival_id | IATA code (e.g., DXB) |
| departure_date | outbound_date | YYYY-MM-DD |
| adults | adults | Default 1 |
| cabin | travel_class | 1=economy, 2=premium, 3=business, 4=first |
| non_stop | stops | 1=nonstop only |
| airlines | include_airlines | Comma-separated IATA codes |
| exclude_airlines | exclude_airlines | Comma-separated IATA codes |
| max_results | (N/A) | Slice results client-side |
| currency | currency | Default USD |

**Fixed params:**
- `engine=google_flights`
- `type=2` (one-way) — we'll add round-trip later
- `hl=en`

### Response Mapping

SerpApi returns `best_flights` and `other_flights` arrays. Each contains:

```json
{
  "flights": [
    {
      "departure_airport": { "name": "...", "id": "JNB", "time": "2026-02-01 10:30" },
      "arrival_airport": { "name": "...", "id": "DXB", "time": "2026-02-01 19:45" },
      "duration": 555,
      "airplane": "Boeing 777",
      "airline": "Emirates",
      "airline_logo": "https://...",
      "flight_number": "EK 766",
      "travel_class": "Economy",
      "legroom": "32 in",
      "extensions": ["Wi-Fi for a fee", "..."]
    }
  ],
  "layovers": [
    { "duration": 90, "name": "Dubai International Airport", "id": "DXB" }
  ],
  "total_duration": 645,
  "price": 520,
  "carbon_emissions": { "this_flight": 525000, "typical_for_this_route": 529000 },
  "booking_token": "...",
  "airline_logo": "https://..."
}
```

**Map to FlightOffer:**
```python
FlightOffer(
    id=booking_token[:16],  # Use as pseudo-ID
    price=Price(amount=price, currency=currency),
    outbound=Itinerary(
        segments=[
            FlightSegment(
                carrier_code=flight["flight_number"].split()[0],
                flight_number=flight["flight_number"].split()[1],
                origin=flight["departure_airport"]["id"],
                destination=flight["arrival_airport"]["id"],
                departure_time=parse_datetime(flight["departure_airport"]["time"]),
                arrival_time=parse_datetime(flight["arrival_airport"]["time"]),
                duration=flight["duration"],
                aircraft=flight.get("airplane"),
                cabin=map_cabin(flight.get("travel_class")),
            )
            for flight in flights
        ],
        duration=total_duration,
    ),
    booking_url=f"https://www.google.com/travel/flights?booking_token={booking_token}"
)
```

### get_flight_schedule() — NOT SUPPORTED

SerpApi doesn't have direct flight number lookup. Return `NotImplementedError` or search-and-filter.

### get_flight_availability() — PARTIAL

Cabin availability not exposed separately. Can infer from search results (which cabins have offers).

### get_seat_map() — NOT SUPPORTED

Google Flights doesn't expose seat maps. Return `None`.

## Price Insights (Bonus)

SerpApi returns `price_insights`:
```json
{
  "lowest_price": 520,
  "price_level": "low",  // "low", "typical", "high"
  "typical_price_range": [690, 1350],
  "price_history": [[1765494000, 520], ...]
}
```

Could expose this as a new method: `get_price_insights(origin, dest, date)`.

## Implementation Plan

1. **Create adapter.py** with working `search_flights()`
2. **Update factory.py** to support `serpapi` provider
3. **Update config.yaml** schema for `serpapi` section
4. **Add .env.example** entry for `SERPAPI_API_KEY`
5. **Test with real API** (free tier: 100 searches/month)

## Limitations vs Amadeus

| Feature | Amadeus | SerpApi |
|---------|---------|---------|
| Flight search | ✅ | ✅ |
| Prices | ✅ (bookable) | ✅ (display only) |
| Flight schedule lookup | ✅ | ❌ |
| Seat availability | ✅ | ❌ |
| Seat map | ✅ | ❌ |
| Direct booking | ✅ | ❌ (links to Google) |
| Rate limits | 2000/mo free | 100/mo free |

## CLI Impact

With SerpApi, we can support:
```bash
fb search JNB DXB 2026-02-01 --cabin J     # ✅ Works
fb flight EK766 today                       # ❌ Not supported
fb avail EK766 today                        # ❌ Not supported  
fb seats EK766 today                        # ❌ Not supported
```

The `search` command is the main use case anyway.
