# Seats.aero Partner API

Award/redemption flight availability across 20+ mileage programs.

## Base URL
```
https://seats.aero/partnerapi
```

## Auth
```
Partner-Authorization: <api_key>
```

## Endpoints

### Cached Search
`GET /search`

Fast search using pre-scraped availability data.

**Params:**
- `origin_airport` (required) - IATA codes, comma-delimited
- `destination_airport` (required) - IATA codes, comma-delimited  
- `start_date` - YYYY-MM-DD
- `end_date` - YYYY-MM-DD
- `cabins` - economy,business,first (comma-delimited)
- `carriers` - AA,DL,UA (comma-delimited)
- `sources` - Mileage programs: aeroplan,united,american,alaska,etc.
- `only_direct_flights` - boolean
- `take` - Max results (10-1000, default 500)
- `order_by` - `lowest_mileage` or default (by date/cabin)

### Live Search
`POST /search`

Real-time search (uses more API quota).

## Response Structure
```json
{
  "data": [{
    "ID": "...",
    "Route": {
      "OriginAirport": "JNB",
      "DestinationAirport": "DXB",
      "Source": "united"
    },
    "Date": "2026-02-14",
    "YAvailable": true,
    "WAvailable": false,
    "JAvailable": true,
    "FAvailable": false,
    "YMileageCost": "45000",
    "JMileageCost": "85000",
    "YAirlines": "EK",
    "JAirlines": "EK",
    "YDirect": true,
    "JDirect": true,
    "Source": "united"
  }]
}
```

## Mileage Programs (sources)
- `aeroplan` - Air Canada
- `united` - United MileagePlus
- `american` - AAdvantage
- `alaska` - Alaska Mileage Plan
- `delta` - Delta SkyMiles
- `virginatlantic` - Flying Club
- `aerlingus` - Avios
- `qantas` - Qantas Points
- `velocity` - Velocity (Virgin Australia)
- `emirates` - Skywards
- `etihad` - Etihad Guest
- `singapore` - KrisFlyer

## Limits
- Pro users: 1,000 API calls/day
- Non-commercial use only without written agreement
