# Flight Buddy

> Quick flight availability lookups from the command line

## Overview

Flight Buddy is a CLI utility for searching flight availability using the Amadeus API. Designed for frequent flyers who want fast answers without opening a browser.

## Core Features

### v1.0 - Search & Availability
- [x] Search one-way flight availability by route
- [x] Filter by departure/arrival airport (IATA codes)
- [x] Filter by date
- [x] Filter by cabin class
- [x] Filter by direct flights only
- [x] **Flight number lookup** (e.g., "EK766 today")
- [x] **Cabin availability by flight** (e.g., "J seats on EK766?")
- [x] **Seat map display** (individual seat availability)
- [x] Display results in a clean, scannable format

### v1.1 - Enhanced Search
- [ ] Round-trip searches
- [ ] Filter by airline (include/exclude)
- [ ] Multiple passengers (adults/children/infants)

### v2.0 - Advanced Features
- [ ] Fare calendar (cheapest days in a range)
- [ ] Multi-city / stopover routing
- [ ] Airport/city search (IATA lookup)
- [ ] Price alerts

### Future Ideas
- [ ] Save favorite routes
- [ ] Price alerts (cron-based)
- [ ] Direct booking links
- [ ] Branded fares comparison

---

## Usage

```bash
# ─────────────────────────────────────────────
# Route Search (origin → destination)
# ─────────────────────────────────────────────

# Basic one-way search
flight-buddy search JNB DXB 2026-02-01

# With cabin class
flight-buddy search JNB DXB 2026-02-01 --cabin business

# Direct flights only
flight-buddy search JNB DXB 2026-02-01 --direct

# Filter by airline
flight-buddy search JNB DXB 2026-02-01 --airline EK,QR

# Short form
fb search JNB DXB 2026-02-01 -c J -d

# ─────────────────────────────────────────────
# Flight Lookup (by flight number)
# ─────────────────────────────────────────────

# Check specific flight
flight-buddy flight EK766 2026-02-01
flight-buddy flight EK766 today

# Check availability on a flight
flight-buddy avail EK766 today
flight-buddy avail EK766 today --cabin business

# Get seat map
flight-buddy seats EK766 today
flight-buddy seats EK766 today --cabin business

# Short forms
fb flight EK766              # defaults to today
fb avail EK766 -c J          # business availability
fb seats EK766               # full seat map
```

## CLI Commands

### `search` - Route Search
```
fb search <origin> <destination> <date> [options]
```

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `origin` | | Departure airport (IATA) | `JNB` |
| `destination` | | Arrival airport (IATA) | `DXB` |
| `date` | | Departure date | `2026-02-01` |
| `--cabin` | `-c` | Cabin class | `economy`, `premium`, `business`, `first` |
| `--adults` | `-a` | Number of adults (1-9) | Default: `1` |
| `--direct` | `-d` | Direct flights only | Flag |
| `--airline` | `-A` | Include airlines (comma-sep) | `EK,QR,SA` |
| `--exclude` | `-X` | Exclude airlines | `LH,AF` |
| `--max` | `-m` | Max results | Default: `10` |
| `--json` | `-j` | JSON output | Flag |

### `flight` - Flight Schedule Lookup
```
fb flight <flight_number> [date]
```

| Argument | Description | Example |
|----------|-------------|---------|
| `flight_number` | Carrier + number | `EK766`, `QR1369` |
| `date` | Date (default: today) | `2026-02-01`, `today`, `tomorrow` |

### `avail` - Cabin Availability
```
fb avail <flight_number> [date] [options]
```

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `flight_number` | | Carrier + number | `EK766` |
| `date` | | Date (default: today) | `today` |
| `--cabin` | `-c` | Filter cabin class | `J` (business) |

### `seats` - Seat Map
```
fb seats <flight_number> [date] [options]
```

| Argument | Short | Description | Example |
|----------|-------|-------------|---------|
| `flight_number` | | Carrier + number | `EK766` |
| `date` | | Date (default: today) | `today` |
| `--cabin` | `-c` | Filter cabin class | `J` (business) |

### Cabin Class Shortcuts

| Input | Amadeus Value |
|-------|---------------|
| `economy`, `eco`, `Y` | `ECONOMY` |
| `premium`, `pey`, `W` | `PREMIUM_ECONOMY` |
| `business`, `biz`, `J` | `BUSINESS` |
| `first`, `F` | `FIRST` |

---

## Output Format

### Route Search (`fb search`)

```
✈  JNB → DXB  ·  Sat 01 Feb 2026  ·  1 adult  ·  Business

Emirates EK764
  07:40 → 18:10 (+0)  ·  8h30m  ·  Direct
  Business (J)  ·  R 24,500

Qatar Airways QR1369 → QR502  
  09:15 → 22:40 (+0)  ·  11h25m  ·  1 stop DOH (2h15m)
  Business (J)  ·  R 19,200

SAA SA234 → SA7102
  14:30 → 08:45 (+1)  ·  16h15m  ·  1 stop JNB (3h)
  Business (J)  ·  R 18,900

─────────────────────────────────────
Showing 3 of 12 results  ·  Prices include taxes
```

### Flight Lookup (`fb flight`)

```
✈  EK766  ·  Emirates  ·  Sat 01 Feb 2026

  JNB  19:20  ───────────────────  DXB  05:50+1
  O.R. Tambo          8h30m          Dubai Intl
  
  Aircraft: Boeing 777-300ER
  Status:   Scheduled
```

### Cabin Availability (`fb avail`)

```
✈  EK766  ·  JNB → DXB  ·  Sat 01 Feb 2026

  Cabin              Avail   
  ─────────────────────────────
  First (F)            4     
  Business (J)         9     ← 
  Premium (W)          —     
  Economy (Y)         82     

  ← = requested cabin
```

### Seat Map (`fb seats`)

```
✈  EK766  ·  JNB → DXB  ·  Business Class

         A   B       C   D       E   F
      ╔═══════════════════════════════════╗
   1  ║  ✓   ✓   │   ✓   ✓   │   ✗   ✓  ║
   2  ║  ✓   ✗   │   ✓   ✓   │   ✓   ✓  ║
   3  ║  ✓   ✓   │   ✗   ✗   │   ✓   ✓  ║
   4  ║  ✓   ✓   │   ✓   ✓   │   ✓   ✗  ║
   5  ║  ✗   ✓   │   ✓   ✗   │   ✓   ✓  ║
      ╚═══════════════════════════════════╝

  ✓ = available  ✗ = occupied  · = blocked
  
  9 of 30 Business seats available
```

### JSON Output (`--json`)

```json
{
  "query": {
    "origin": "JNB",
    "destination": "DXB", 
    "date": "2026-02-01",
    "cabin": "BUSINESS",
    "adults": 1
  },
  "results": [
    {
      "price": { "amount": 24500, "currency": "ZAR" },
      "itinerary": {
        "duration": "PT8H30M",
        "segments": [
          {
            "flight": "EK764",
            "departure": { "airport": "JNB", "time": "2026-02-01T07:40:00" },
            "arrival": { "airport": "DXB", "time": "2026-02-01T18:10:00" },
            "duration": "PT8H30M",
            "cabin": "BUSINESS"
          }
        ]
      }
    }
  ]
}
```

---

## API Reference

### Authentication

OAuth2 Client Credentials flow:

```
POST /v1/security/oauth2/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials
&client_id={API_KEY}
&client_secret={API_SECRET}
```

Returns `access_token` (valid ~30 min).

### Flight Offers Search

**Endpoint:** `GET /v2/shopping/flight-offers`

**Query Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `originLocationCode` | ✓ | IATA code |
| `destinationLocationCode` | ✓ | IATA code |
| `departureDate` | ✓ | YYYY-MM-DD |
| `returnDate` | | YYYY-MM-DD (for round-trip) |
| `adults` | ✓ | 1-9 |
| `children` | | 0-9 |
| `infants` | | 0-9 |
| `travelClass` | | ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST |
| `includedAirlineCodes` | | Comma-separated IATA airline codes |
| `excludedAirlineCodes` | | Comma-separated IATA airline codes |
| `nonStop` | | true/false |
| `currencyCode` | | ISO currency (default: airline's) |
| `max` | | Max results (default: 250) |

**Response Structure:**
```
{
  "data": [
    {
      "id": "1",
      "source": "GDS",
      "price": { "total": "245.00", "currency": "EUR" },
      "itineraries": [
        {
          "duration": "PT8H30M",
          "segments": [...]
        }
      ],
      "travelerPricings": [...]
    }
  ],
  "dictionaries": {
    "carriers": { "EK": "EMIRATES" },
    "aircraft": { "388": "AIRBUS A380" },
    "locations": { "JNB": {...} }
  }
}
```

### Flight Schedule (for `fb flight`)

**Endpoint:** `GET /v2/schedule/flights`

| Param | Required | Description |
|-------|----------|-------------|
| `carrierCode` | ✓ | 2-letter IATA airline code |
| `flightNumber` | ✓ | Flight number (digits only) |
| `scheduledDepartureDate` | ✓ | YYYY-MM-DD |

### Flight Availabilities (for `fb avail`)

**Endpoint:** `POST /v1/shopping/availability/flight-availabilities`

Request body specifies origin/destination/date/time, returns availability by booking class (F9, J6, Y82 etc.)

### Seat Maps (for `fb seats`)

**Endpoint:** `POST /v1/shopping/seatmaps`

Requires a flight offer from Flight Offers Search. Returns deck layout with individual seat availability, characteristics (window, aisle, extra legroom), and amenities.

### Other Endpoints (Future)

| Endpoint | Description |
|----------|-------------|
| `GET /v1/shopping/flight-dates` | Cheapest dates in range |
| `GET /v1/reference-data/locations` | Airport/city search |

---

## Implementation Checklist

### Phase 1: Foundation ✅
- [x] Project setup
  - [x] Create `requirements.txt`
  - [x] Create package structure (`app/`)
  - [ ] Set up `pyproject.toml` or `setup.py`
- [x] Auth module (`auth.py`)
  - [x] OAuth2 token fetch
  - [x] Token caching (avoid re-auth every call)
  - [x] Token refresh on expiry
- [x] API client (`client.py`)
  - [x] Base HTTP client with auth headers
  - [x] Error handling (rate limits, 4xx, 5xx)
  - [x] Response parsing (`models.py`)

### Phase 2: Core Commands ✅
- [x] CLI framework (`cli.py`)
  - [x] Click app setup
  - [x] `search` subcommand
  - [x] `flight` subcommand
  - [x] `avail` subcommand
  - [x] `seats` subcommand (API working, visual in Phase 3)
  - [x] Global options (`--json`, `--help`)
- [x] Flight Offers Search (`search`)
  - [x] Build query params from CLI args
  - [x] Parse response into model
  - [x] Handle cabin class mapping
  - [x] Handle airline filters
- [x] Flight Schedule (`flight`)
  - [x] Parse flight number (EK766 → EK + 766)
  - [x] Handle date shortcuts (today, tomorrow)
  - [x] Call schedule API
- [x] Flight Availability (`avail`)
  - [x] Get schedule first (for origin/dest)
  - [x] Call availability API
  - [x] Parse booking class availability
- [x] Seat Maps (`seats`)
  - [x] Get flight offer first
  - [x] Call seatmaps API
  - [x] Parse deck/seat layout

### Phase 3: Output Formatting ✅
- [x] Formatter module (`formatter.py`)
  - [x] Route search table
  - [x] Flight schedule display
  - [x] Availability table
  - [x] ASCII seat map
  - [x] JSON output mode
- [x] Rich integration
  - [x] Colors and styling
  - [x] Tables
  - [x] Progress indicators (not needed for CLI)

### Phase 4: Polish ✅
- [x] Error messages (user-friendly)
- [x] Help text for all commands
- [x] `fb` alias setup instructions
- [x] README.md
- [x] Basic tests (9 passing)

---

## Technical Design

### Project Structure

```
flight-buddy/
├── .env                 # API credentials
├── .gitignore
├── spec.md              # This file
├── requirements.txt     # Python deps
├── app/
│   ├── __init__.py
│   ├── cli.py           # CLI entry point (argparse/click)
│   ├── client.py        # Amadeus API client
│   ├── auth.py          # OAuth token management
│   ├── models.py        # Response parsing
│   └── formatter.py     # Output formatting
└── tests/
```

### Dependencies

```
httpx          # HTTP client (async support)
python-dotenv  # .env loading  
rich           # Terminal formatting
click          # CLI framework
```

### Environment

```bash
# .env
AMADEUS_API_KEY=xxx
AMADEUS_API_SECRET=xxx
AMADEUS_BASE_URL=https://test.api.amadeus.com  # or api.amadeus.com for prod
```

---

## Development

```bash
# Setup
cd ~/Blink/custom/flight-buddy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python -m src JNB DXB 2026-02-01

# Or with alias
alias fb='python -m src'
fb JNB DXB 2026-02-01 -c J
```

---

## Notes

- Sandbox returns cached/test data, not live availability
- Production requires Amadeus approval for higher rate limits
- Prices in sandbox may not reflect real fares
- 2000 free API calls/month on self-service tier

---

*Built for Wiza by Blink 🛫*
