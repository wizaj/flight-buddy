# ✈ Flight Buddy

Fast flight searches from the command line. Built for frequent flyers who want answers without opening a browser.

## Installation

```bash
git clone https://github.com/wizaj/flight-buddy.git
cd flight-buddy
pip install -e .
```

Then add an alias to your shell (`~/.zshrc` or `~/.bashrc`):

```bash
alias fb='python -m src.cli'
```

## Quick Start

```bash
# Search flights
fb search JNB DXB tomorrow

# Business class, direct only
fb search JNB DXB 2026-02-14 --cabin J --direct

# Award availability (miles)
fb awards JNB DXB 2026-02-14

# Seat availability by fare class (ExpertFlyer)
fb ef-avail JNB NBO friday --airline KQ --cabin J
```

---

## Commands

### `fb search` — Flight Search

Search cash fares via Google Flights.

```bash
fb search <origin> <destination> <date> [options]

# Examples
fb search JNB DXB tomorrow
fb search JNB DXB 2026-02-14 --return 2026-02-21
fb search JNB DXB 2026-02-14 --cabin J --direct
fb search JNB DXB 2026-02-14 --airline EK,QR
fb search JNB DXB 2026-02-14 --exclude SA
```

| Option | Short | Description |
|--------|-------|-------------|
| `--return` | `-r` | Return date (round-trip) |
| `--cabin` | `-c` | Cabin: Y/W/J/F |
| `--direct` | `-d` | Direct flights only |
| `--airline` | `-A` | Include airlines (IATA codes) |
| `--exclude` | `-X` | Exclude airlines |
| `--json` | `-j` | JSON output |

---

### `fb awards` — Award Search

Search award availability across 20+ mileage programs via Seats.aero.

```bash
fb awards <origin> <destination> <date> [options]

# Examples
fb awards JNB DXB 2026-02-14
fb awards JNB DXB 2026-02-14 --cabin J --direct
fb awards JNB DXB 2026-02-14 --program emirates,qantas
fb awards JNB DXB 2026-02-14 --end-date 2026-02-21 --cheapest
```

| Option | Description |
|--------|-------------|
| `--cabin` | Cabin: Y/W/J/F |
| `--direct` | Direct flights only |
| `--program` | Filter programs (comma-separated) |
| `--end-date` | Search date range |
| `--cheapest` | Sort by miles cost |
| `--airline` | Filter by operating airline |

**Supported Programs:** Aeroplan, United, AAdvantage, Alaska, Delta, Virgin Atlantic, Qantas, Emirates, Etihad, KrisFlyer, LifeMiles, and more.

---

### `fb ef-avail` — Fare Class Availability

Check real-time seat inventory by fare class via ExpertFlyer. Essential for upgrade planning and award bookings.

```bash
fb ef-avail <origin> <destination> <date> [options]

# Examples
fb ef-avail JNB NBO friday
fb ef-avail JNB CDG 2026-02-01 --airline AF
fb ef-avail JNB NBO tomorrow --cabin J
fb ef-avail JNB AMS 2026-02-01 --fares J,C,D,I,Z
```

| Option | Short | Description |
|--------|-------|-------------|
| `--airline` | `-a` | Filter by airline (IATA code) |
| `--cabin` | `-c` | Filter: J=business, Y=economy |
| `--fares` | `-f` | Show specific fare classes |
| `--compact` | | Single-line output |
| `--json` | `-j` | JSON output |

**Output Example:**
```
✈ KQ 761 JNB→NBO 12:05 PM (737-800)

Business:
• J (9) fully flexible
• C (9) minor restrictions  
• D (9) moderate restrictions
• I (9) lower miles earning
• Z (9) least flexible

Economy:
• Y (9) fully flexible
• B (9) light restrictions
• M (9) moderate discount
```

---

### `fb balance` — Mileage Balances

Track your frequent flyer balances to see affordability in award searches.

```bash
fb balance                              # View all
fb balance update emirates 72290        # Update balance
fb balance update emirates 85000 --tier Gold --note "DXB trip"
fb balance history emirates             # View history
```

---

## Fare Class Reference

### Business Class

| Code | Name | Description |
|------|------|-------------|
| **J** | Full Fare | Fully flexible, full miles, upgradeable |
| **C** | Business | Minor restrictions, good miles earning |
| **D** | Discounted | Moderate restrictions |
| **I** | Business Promo | Lower miles earning rate |
| **Z** | Lowest Business | Least flexible, often used for awards |

### Premium Economy

| Code | Name | Description |
|------|------|-------------|
| **W** | Premium Economy | Standard premium cabin fare |
| **P** | Discounted PE | Restricted premium economy |

### Economy

| Code | Name | Description |
|------|------|-------------|
| **Y** | Full Fare | Fully flexible, full miles |
| **B** | Economy | Light restrictions |
| **M** | Moderate | Standard discount fare |
| **H** | Economy | Mid-tier discount |
| **K** | Economy | Advance purchase |
| **L** | Low | Restricted, low miles |
| **Q** | Discounted | Deep discount |
| **T** | Discounted | Deep discount |
| **V** | Discounted | Very restricted |
| **X** | Lowest | Basic economy, no changes |

### Award Classes (varies by airline)

| Code | Typical Use |
|------|-------------|
| **I** | Business award (many airlines) |
| **Z** | Business award/upgrade |
| **O** | Business award (overflow) |
| **X** | Economy award |
| **N** | Economy award (restricted) |

**Note:** Fare class definitions vary by airline. The above are common patterns but always verify with the specific carrier.

---

## Cabin Codes

| Code | Class |
|------|-------|
| **Y** | Economy |
| **W** | Premium Economy |
| **J** | Business |
| **F** | First |

---

## Configuration

Create `~/.flight-buddy/.env` or set environment variables:

```bash
# Google Flights (via SerpApi) — default provider
SERPAPI_API_KEY=xxx

# Award search (Seats.aero Pro)
SEATSAERO_API_KEY=pro_xxx

# ExpertFlyer (fare class availability)
EXPERTFLYER_EMAIL=you@email.com
EXPERTFLYER_PASSWORD=yourpassword

# Optional: Amadeus GDS
AMADEUS_API_KEY=xxx
AMADEUS_API_SECRET=xxx
```

### API Keys

| Provider | Get Key | Cost |
|----------|---------|------|
| **SerpApi** | [serpapi.com](https://serpapi.com) | 100 free/mo, then $50/5k |
| **Seats.aero** | [seats.aero/settings](https://seats.aero/settings) | $10/mo Pro |
| **ExpertFlyer** | [expertflyer.com](https://expertflyer.com) | $9.99/mo Premium |
| **Amadeus** | [developers.amadeus.com](https://developers.amadeus.com) | Free sandbox |

---

## Tips

### For Upgrades
Check the **lowest fare class** in your target cabin. If you see Z9 (business) and you're booked in Y, there's upgrade space.

### For Award Bookings
Different programs release different inventory:
- **Emirates Skywards** often shows more J space than partners
- **Aeroplan** can access partner space others can't
- **United** dynamically prices, so costs vary

### Understanding Availability Numbers
- **9** = 9 or more seats available
- **4** = exactly 4 seats
- **0** = sold out or not offered

---

## License

MIT
