# ✈ Flight Buddy

Quick flight availability lookups from the command line. Built for frequent flyers who want fast answers without opening a browser.

## Features

- 🔍 Search flights by route and date
- 💺 Filter by cabin class (economy/business/first)
- ✈️ Direct flights only filter
- 🏢 Airline include/exclude filters
- 💰 Price insights from Google Flights
- 📊 JSON output for scripting

## Providers

Flight Buddy supports multiple data providers:

| Provider | Status | Best For | Limits |
|----------|--------|----------|--------|
| **SerpApi** | ✅ Active | Real-time prices, quick lookups | 100/mo free |
| **Amadeus** | 🔒 Sandbox | Full booking flow, seat maps | Needs approval |
| **Duffel** | 🚧 Planned | Booking, African airlines | US entity required |

Default: **SerpApi** (Google Flights data, no approval needed)

## Install

```bash
# Clone
git clone https://github.com/wizaj/flight-buddy.git
cd flight-buddy

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Add your API key(s) to .env
```

## API Keys

**SerpApi (recommended):**
1. Sign up at https://serpapi.com
2. Get key from https://serpapi.com/manage-api-key
3. Add to `.env`: `SERPAPI_API_KEY=xxx`

**Amadeus (optional):**
1. Sign up at https://developers.amadeus.com
2. Create an app to get credentials
3. Add to `.env`: `AMADEUS_API_KEY=xxx` and `AMADEUS_API_SECRET=xxx`

## Usage

### Setup Alias

Add to your shell config (`~/.bashrc` or `~/.zshrc`):

```bash
alias fb='python -m src'
# Or with full path:
alias fb='/path/to/flight-buddy/venv/bin/python -m src'
```

### Search Flights

```bash
# Basic search
fb search JNB DXB 2026-02-01

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

### Cabin Classes

| Code | Class |
|------|-------|
| Y | Economy |
| W | Premium Economy |
| J | Business |
| F | First |

### Provider Selection

Set in `config.yaml`:

```yaml
provider: serpapi  # or: amadeus, duffel
```

Or use environment variable:

```bash
FLIGHT_BUDDY_PROVIDER=amadeus fb search JNB DXB 2026-02-01
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--cabin` | `-c` | Cabin class: Y, W, J, F |
| `--adults` | `-a` | Number of passengers (1-9) |
| `--direct` | `-d` | Direct flights only |
| `--airline` | `-A` | Include airlines (comma-separated) |
| `--exclude` | `-X` | Exclude airlines |
| `--max` | `-m` | Max results (default: 10) |
| `--currency` | | Currency code (default: USD) |
| `--json` | `-j` | JSON output |

## Examples

```bash
# "Cheapest business class JNB to Dubai next month?"
fb search JNB DXB 2026-02-01 -c J -m 5

# "Direct Emirates flights only"
fb search JNB DXB 2026-02-01 -A EK -d

# "Anything except SAA?"
fb search JNB DXB 2026-02-01 -X SA
```

## Provider Comparison

### SerpApi (Google Flights)
- ✅ Real-time prices
- ✅ No approval needed
- ✅ Price insights (lowest price, typical range)
- ❌ No seat maps
- ❌ No flight number lookup
- ❌ Display only (links to Google for booking)

### Amadeus
- ✅ Full booking capability
- ✅ Seat maps
- ✅ Flight schedules
- ✅ Seat availability by class
- ❌ Requires production approval
- ❌ Sandbox has fake data

### Duffel
- ✅ Modern API, easy auth
- ✅ Good African airline coverage (via Travelport)
- ❌ Requires US entity/SSN
- 🚧 Not yet implemented

## Development

```bash
cd ~/flight-buddy
source venv/bin/activate

# Run tests
pytest

# Run directly
python -m src search JNB DXB 2026-02-01
```

## License

MIT

---

*Built by Blink 🛫*
