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

### Search Award Flights (Miles/Points)

Search for award redemption availability across 20+ mileage programs using Seats.aero.

```bash
# Basic award search
fb awards JNB DXB 2026-02-14

# Business class awards only
fb awards JNB DXB 2026-02-14 --cabin J

# Direct awards only
fb awards JNB DXB 2026-02-14 --direct

# Search specific mileage programs
fb awards JNB DXB 2026-02-14 --program aeroplan,united,emirates

# Date range search
fb awards JNB DXB 2026-02-14 --end-date 2026-02-21

# Sort by cheapest miles
fb awards JNB DXB 2026-02-14 --cheapest

# Filter by operating airline
fb awards JNB DXB 2026-02-14 --airline EK

# JSON output
fb awards JNB DXB 2026-02-14 --json
```

**Award Search Output:**
```
✈  JNB → DXB  •  Award Search  •  2026-02-14

  2026-02-14
  ────────────────────────────────────────────────────────────
    Emirates Skywards        B: 91,500 ✓   |  E: 20,000 ✓💰
    Qantas                   B: 82,100 ✓💰 |  E: 29,000 ✓💰
    United MileagePlus       B: 90,000     |  E: 35,000
```

**Legend:** B=Business, E=Economy, ✓=Direct, 💰=Affordable (based on your balance)

### Manage Mileage Balances

Track your frequent flyer balances to see affordability in award searches.

```bash
# View all balances
fb balance

# Update a balance
fb balance update emirates 72290 --tier Gold

# Update with note (for tracking)
fb balance update emirates 85000 --note "Miles posted from DXB trip"

# View balance history
fb balance history emirates
```

**Balance Output:**
```
✈  Mileage Balances
──────────────────────────────────────────────────
  Emirates Skywards         72,290 [Gold]
  ShebaMiles                64,920 [Silver]
  British Airways Avios     50,261 [5156 TP]
  Flying Blue               12,416 [Gold]

  Total                    199,887
  Est. value              $  1,999
```

**Affordability Indicators in Award Search:**
- 💰 = You can afford this redemption
- ⚠️ = Close (within 10k miles)
- *(no icon)* = Need more miles or program not tracked

**History Tracking:**
```
fb balance update emirates 85000 --note "DXB trip posted"

✓ Updated Emirates Skywards
  Balance: 85,000 (+12,710)
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

| Feature | SerpApi | Amadeus | Seats.aero | Duffel |
|---------|:-------:|:-------:|:----------:|:------:|
| **Flight Search (Cash)** | ✅ | ✅ | ❌ | 🚧 |
| **Award Search (Miles)** | ❌ | ❌ | ✅ | ❌ |
| **Balance Tracking** | ❌ | ❌ | ✅ | ❌ |
| **Affordability Check** | ❌ | ❌ | ✅ | ❌ |
| **Round-trip Search** | ✅ | ❌ | ✅ | 🚧 |
| **Real-time Prices** | ✅ | ⚠️ | ✅ | 🚧 |
| **Multi-Program Compare** | ❌ | ❌ | ✅ | ❌ |
| **Flight Schedule Lookup** | ❌ | ✅ | ❌ | ❌ |
| **Seat Availability by Class** | ❌ | ✅ | ✅ | 🚧 |
| **Seat Maps** | ❌ | ✅ | ❌ | ⚠️ |
| **Booking** | ❌ | ✅ | ❌ | ✅ |
| **African Airline Coverage** | ✅ | ⚠️ | ✅ | ✅ |

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

### Seats.aero

Award/redemption flight availability across 20+ mileage programs.

**Pros:**
- Search award availability across Aeroplan, United, American, Emirates, Qantas, etc.
- Compare mileage costs across programs instantly
- Real-time availability data
- Filter by cabin class, direct flights, specific programs
- No booking needed (use airline site to book)

**Cons:**
- Award flights only (no cash prices)
- Requires Pro subscription ($10/mo)
- 1,000 API calls/day limit
- Non-commercial use only (without agreement)

**Setup:**
1. Get Pro subscription at https://seats.aero
2. Generate API key at https://seats.aero/settings (API tab)
3. Add to `.env`: `SEATSAERO_API_KEY=pro_xxx`

**Commands:**
```bash
# Basic award search
fb awards JNB DXB 2026-02-14

# Business class, direct only
fb awards JNB DXB 2026-02-14 --cabin J --direct

# Search specific programs
fb awards JNB DXB 2026-02-14 --program emirates,qantas

# Date range, sorted by cheapest
fb awards JNB DXB 2026-02-14 -e 2026-02-21 --cheapest

# Manage your mileage balances
fb balance
fb balance update emirates 72290 --tier Gold
fb balance history emirates
```

**Supported Programs:**
Aeroplan, United MileagePlus, AAdvantage, Alaska Mileage Plan, Delta SkyMiles,
Virgin Atlantic, Qantas, Emirates Skywards, Etihad Guest, KrisFlyer, LifeMiles, Smiles, and more.

**Balance Tracking:**
Store your mileage balances to see 💰 affordability indicators in award search results.
Deltas are tracked automatically when you update balances.

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
