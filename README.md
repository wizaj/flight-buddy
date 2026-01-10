# ✈ Flight Buddy

Quick flight availability lookups from the command line.

## Install

```bash
# Clone
git clone git@github.com:wizaj/flight-buddy.git
cd flight-buddy

# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Amadeus API credentials
```

## Setup Alias

Add to your `~/.bashrc` or `~/.zshrc`:

```bash
alias fb='python -m flight_buddy'
```

Or for the full path:

```bash
alias fb='/path/to/flight-buddy/venv/bin/python -m flight_buddy'
```

Then reload: `source ~/.bashrc`

## Usage

### Search Flights

```bash
# Basic search
fb search JNB DXB 2026-02-01

# With cabin class (J=business, Y=economy, F=first, W=premium)
fb search JNB DXB tomorrow --cabin J

# Direct flights only
fb search JNB DXB 2026-02-01 --direct

# Filter by airline
fb search JNB DXB 2026-02-01 --airline EK,QR
```

### Flight Schedule

```bash
# Look up a flight
fb flight EK766 today
fb flight QR1369 2026-02-01
```

### Cabin Availability

```bash
# Check how many seats available by class
fb avail EK766 today
fb avail EK766 tomorrow --cabin J
```

### Seat Map

```bash
# View seat map
fb seats TP942 2026-02-15

# Filter by cabin
fb seats EK766 today --cabin business
```

## Options

| Option | Short | Description |
|--------|-------|-------------|
| `--cabin` | `-c` | Cabin class: economy/Y, premium/W, business/J, first/F |
| `--adults` | `-a` | Number of passengers (1-9) |
| `--direct` | `-d` | Direct flights only |
| `--airline` | `-A` | Include airlines (comma-separated) |
| `--exclude` | `-X` | Exclude airlines |
| `--max` | `-m` | Max results (default: 10) |
| `--currency` | | Currency code (default: USD) |
| `--json` | `-j` | JSON output |

## API

Uses [Amadeus Self-Service API](https://developers.amadeus.com/self-service). 
Free tier: 2000 calls/month.

Get credentials at: https://developers.amadeus.com

## Examples

```bash
# "What's the cheapest business class JNB to Dubai next month?"
fb search JNB DXB 2026-02-01 -c J -m 5

# "Any J seats on Emirates 766 today?"
fb avail EK766 today -c J

# "Show me the seat map"
fb seats EK766 today
```

## License

MIT

---

*Built by Blink 🛫*
