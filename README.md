# ✈ Flight Buddy

Quick flight lookups from the command line. Built for frequent flyers who want fast answers without opening a browser.

## Quick Start

```bash
# One-way search
fb search JNB DXB 2026-02-01

# Round-trip search
fb search JNB NBO 2026-01-23 --return 2026-01-30

# Business class, direct only
fb search JNB DXB tomorrow -c J -d
```

## Installation

```bash
git clone https://github.com/wizaj/flight-buddy.git
cd flight-buddy
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your SERPAPI_API_KEY to .env
```

### Shell Alias

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias fb='cd ~/path/to/flight-buddy && source venv/bin/activate && python -m src.cli'
```

## Usage

### Search Flights

```bash
# Basic one-way
fb search JNB DXB 2026-02-01

# Round-trip (uses --return or -r)
fb search JNB NBO 2026-01-23 -r 2026-01-30

# Business class
fb search JNB DXB tomorrow --cabin J

# Direct flights only
fb search JNB DXB 2026-02-01 --direct

# Filter by airline
fb search JNB DXB 2026-02-01 --airline EK,QR

# Exclude airlines
fb search JNB DXB 2026-02-01 --exclude SA

# JSON output (for scripting)
fb search JNB DXB 2026-02-01 --json
```

### Output Format

**One-way:**
```
✈  JNB → NBO  •  Fri 23 Jan 2026  •  1 adult

DIRECT FLIGHTS ────────────────────────────────────
  Kenya KQ761    12:05 → 17:10        $979   • Boeing 737
  Airlink 4Z70   09:40 → 14:40      $1,270   • Embraer 190

CONNECTING ───────────────────────────────────────
  RwandAir WB103  03:10 → 20:10      $521   • 1 stop KGL
```

**Round-trip:**
```
✈  JNB ↔ NBO  •  Fri 23 Jan 2026 → Fri 30 Jan  •  1 adult

DIRECT ────────────────────────────────────────────
  Airlink  09:40→14:40  ⇄  15:30→18:40  $1,816
    OUT 4Z70  •  RET 4Z71

CONNECTING ───────────────────────────────────────
  RwandAir  03:10→20:10 (1x)  ⇄  05:30→15:40 (1x)  $811
    OUT WB103+WB402  •  RET WB464+WB108
```

### Search Options

| Option | Short | Description |
|--------|-------|-------------|
| `--return` | `-r` | Return date for round-trip |
| `--cabin` | `-c` | Cabin class: Y, W, J, F |
| `--adults` | `-a` | Number of passengers (1-9) |
| `--direct` | `-d` | Direct flights only |
| `--airline` | `-A` | Include airlines (comma-separated IATA) |
| `--exclude` | `-X` | Exclude airlines |
| `--max` | `-m` | Max results (default: 10) |
| `--currency` | | Currency code (default: USD) |
| `--json` | `-j` | JSON output |

### Cabin Codes

| Code | Class |
|------|-------|
| Y | Economy |
| W | Premium Economy |
| J | Business |
| F | First |

---

## Providers

Flight Buddy supports multiple data providers. Set in `config.yaml` or via environment:

```bash
FLIGHT_BUDDY_PROVIDER=amadeus fb search JNB DXB 2026-02-01
```

### Feature Comparison

| Feature | SerpApi | Amadeus | Duffel |
|---------|:-------:|:-------:|:------:|
| **Flight Search** | ✅ | ✅ | 🚧 |
| **Round-trip Search** | ✅ | ❌ | 🚧 |
| **Real-time Prices** | ✅ | ⚠️ | 🚧 |
| **Price Insights** | ✅ | ❌ | ❌ |
| **Flight Schedule Lookup** | ❌ | ✅ | ❌ |
| **Seat Availability by Class** | ❌ | ✅ | 🚧 |
| **Seat Maps** | ❌ | ✅ | ⚠️ |
| **Booking** | ❌ | ✅ | ✅ |
| **African Airline Coverage** | ✅ | ⚠️ | ✅ |

✅ = Available  ⚠️ = Limited/Sandbox  ❌ = Not available  🚧 = Not yet implemented

### SerpApi (Default)

Scrapes Google Flights for real-time prices and availability.

**Pros:**
- Real-time prices from Google Flights
- No approval needed (just API key)
- Price insights (lowest price, typical range)
- Full round-trip support with both legs
- Good coverage of all airlines

**Cons:**
- Display only (no booking)
- No flight number lookup
- No seat maps or cabin availability

**Setup:**
1. Sign up at https://serpapi.com
2. Get key from https://serpapi.com/manage-api-key
3. Add to `.env`: `SERPAPI_API_KEY=xxx`

**Limits:** 100 searches/month free, then $50/mo for 5,000

### Amadeus

Full GDS access with booking capabilities.

**Pros:**
- Flight schedule lookup by flight number (`fb flight EK766`)
- Seat availability by cabin class (`fb avail EK766 -c J`)
- Seat maps (`fb seats EK766`)
- Can book flights (production only)

**Cons:**
- Sandbox has fake/outdated data
- Production requires business approval
- No round-trip in single query (yet)
- Some African carriers missing

**Setup:**
1. Sign up at https://developers.amadeus.com
2. Create an app for credentials
3. Add to `.env`:
   ```
   AMADEUS_API_KEY=xxx
   AMADEUS_API_SECRET=xxx
   ```

**Commands (Amadeus only):**
```bash
# Flight schedule lookup
fb flight EK766 tomorrow

# Seat availability by cabin
fb avail EK766 2026-02-01 --cabin J

# Seat map
fb seats EK766 2026-02-01
```

### Duffel

Modern API with good African coverage via Travelport.

**Status:** 🚧 Not yet implemented

**Would support:**
- Flight search and booking
- 19 African airlines via Travelport GDS
- Simpler API than Amadeus

**Blockers:**
- Requires US entity/SSN for signup
- £2.20/order + 1% pricing

---

## Examples

### Common Searches

```bash
# Cheapest business class to Dubai
fb search JNB DXB 2026-02-01 -c J

# Weekend trip to Nairobi
fb search JNB NBO 2026-02-07 -r 2026-02-09

# Direct Emirates flights only
fb search JNB DXB 2026-02-01 -A EK -d

# Avoid SAA
fb search JNB CPT tomorrow -X SA

# Multiple airlines
fb search JNB LHR 2026-03-01 -A BA,VS,SA
```

### Scripting with JSON

```bash
# Get cheapest price
fb search JNB DXB 2026-02-01 -j | jq '.results[0].price.amount'

# List all direct flights
fb search JNB NBO 2026-01-23 -d -j | jq '.results[].itinerary.segments[0].flight'
```

---

## Development

```bash
cd ~/flight-buddy
source venv/bin/activate

# Run tests
pytest

# Run directly
python -m src.cli search JNB DXB 2026-02-01
```

## License

MIT

---

*Built with ☕ by Blink*
