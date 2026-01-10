# Flight Buddy

> Quick flight availability lookups from the command line

## Overview

Flight Buddy is a CLI utility for searching flight availability using the Amadeus API. Designed for frequent flyers who want fast answers without opening a browser.

## Core Features

### v1.0 - Basic Search
- Search one-way flight availability
- Filter by departure/arrival airport (IATA codes)
- Filter by date
- Filter by cabin class
- Display results in a clean, scannable format

### Future Ideas
- Round-trip searches
- Multi-city / stopover routing
- Fare calendar (cheapest days)
- Seat map lookups
- Save favorite routes
- Price alerts
- Direct booking links

## Usage

```bash
# Basic one-way search
flight-buddy JNB DXB 2026-02-01

# With cabin class
flight-buddy JNB DXB 2026-02-01 --cabin business

# Short aliases
fb JNB DXB 2026-02-01 -c J
```

## Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `origin` | Departure airport (IATA) | `JNB` |
| `destination` | Arrival airport (IATA) | `DXB` |
| `date` | Departure date (YYYY-MM-DD) | `2026-02-01` |
| `--cabin`, `-c` | Cabin class | `economy`, `premium`, `business`, `first` (or `Y`, `W`, `J`, `F`) |
| `--adults`, `-a` | Number of adults | Default: `1` |
| `--direct`, `-d` | Direct flights only | Flag |
| `--max`, `-m` | Max results | Default: `10` |

## Output Format

```
JNB → DXB  |  Sat 01 Feb 2026

Emirates EK764
  07:40 → 18:10 (8h30m) · Direct
  Business (J) · ZAR 24,500

Qatar Airways QR1369 → QR502  
  09:15 → 22:40 (11h25m) · via DOH (2h15m layover)
  Business (J) · ZAR 19,200

[3 more results...]
```

## Technical Notes

### API
- **Provider:** Amadeus Self-Service API
- **Endpoint:** Flight Offers Search v2
- **Auth:** OAuth2 (client credentials)
- **Environment:** Sandbox (test.api.amadeus.com)

### Cabin Class Mapping
| Input | Amadeus Code |
|-------|--------------|
| `economy`, `Y` | `ECONOMY` |
| `premium`, `W` | `PREMIUM_ECONOMY` |
| `business`, `J` | `BUSINESS` |
| `first`, `F` | `FIRST` |

## Development

```bash
# Setup
cd ~/Blink/custom/flight-buddy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run
python flight_buddy.py JNB DXB 2026-02-01
```

## API Reference

Postman collection: `./amadeus.postman_collection.json`

---

*Built for Wiza by Blink 🛫*
