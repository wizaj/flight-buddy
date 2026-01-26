#!/usr/bin/env python3
"""
ExpertFlyer scraper using agent-browser for flight-buddy.

Usage:
    python scraper.py search JNB AMS 2026-01-31
    python scraper.py search JNB AMS 2026-01-31 --airline KL
"""

import subprocess
import json
import re
import sys
from dataclasses import dataclass, field
from typing import Optional


# Fare class descriptions
FARE_CLASSES = {
    # Business Class
    "J": ("Business", "Full fare business — fully flexible"),
    "C": ("Business", "Business — minor restrictions"),
    "D": ("Business", "Discounted business — moderate restrictions"),
    "I": ("Business", "Discounted business — lower miles earning"),
    "Z": ("Business", "Deep discount business — least flexible"),
    
    # Premium Economy
    "O": ("Premium", "Premium economy — standard"),
    "W": ("Premium", "Premium economy — discounted"),
    
    # Economy (full fare)
    "Y": ("Economy", "Full fare economy — fully flexible"),
    
    # Economy (discounted tiers)
    "B": ("Economy", "Economy — light restrictions"),
    "M": ("Economy", "Economy — moderate discount"),
    "U": ("Economy", "Economy — discounted"),
    "K": ("Economy", "Economy — discounted"),
    "H": ("Economy", "Economy — discounted"),
    "L": ("Economy", "Economy — discounted"),
    "Q": ("Economy", "Economy — discounted"),
    "T": ("Economy", "Economy — deep discount"),
    "E": ("Economy", "Economy — deep discount"),
    "N": ("Economy", "Economy — deep discount"),
    "R": ("Economy", "Economy — restricted (varies by airline)"),
    "V": ("Economy", "Economy — deep discount"),
    "X": ("Economy", "Economy — deep discount"),
    
    # Special
    "S": ("Economy", "Economy — special fare"),
    "A": ("Special", "First/Economy discount (varies by airline)"),
    "F": ("First", "Full fare first class"),
    "P": ("First", "First class — discounted"),
}


@dataclass
class FareAvailability:
    """Availability for a single fare class."""
    fare_class: str
    seats: int
    cabin: str
    description: str


@dataclass
class FlightAvailability:
    """Complete availability for a flight."""
    flight: str
    origin: str
    destination: str
    depart: str
    arrive: str
    aircraft: str
    frequency: str
    availability: dict  # {"J": 9, "C": 9, "D": 5, ...}
    stops: int = 0
    
    @property
    def fare_details(self) -> list[FareAvailability]:
        """Get detailed fare availability list."""
        details = []
        for fare_class, seats in self.availability.items():
            cabin, desc = FARE_CLASSES.get(
                fare_class, 
                ("Unknown", f"Unknown fare class {fare_class}")
            )
            details.append(FareAvailability(
                fare_class=fare_class,
                seats=seats,
                cabin=cabin,
                description=desc
            ))
        return details

    def business_seats(self) -> int:
        """Return total business class seats (J + C + D + I + Z)."""
        return sum(self.availability.get(c, 0) for c in ['J', 'C', 'D', 'I', 'Z'])

    def premium_seats(self) -> int:
        """Return premium economy seats."""
        return sum(self.availability.get(c, 0) for c in ['O', 'W'])

    def economy_seats(self) -> int:
        """Return economy seats (Y + B + M + ...)."""
        return sum(
            self.availability.get(c, 0) 
            for c in ['Y', 'B', 'M', 'H', 'K', 'L', 'Q', 'T', 'E', 'N', 'R', 'V', 'X']
        )


def parse_availability_string(avail_str: str) -> dict:
    """Parse 'J9C9D5Q0I0Y9B9M9' into {'J': 9, 'C': 9, 'D': 5, ...}."""
    result = {}
    # Match letter followed by digit(s)
    matches = re.findall(r'([A-Z])(\d+)', avail_str)
    for letter, count in matches:
        result[letter] = int(count)
    return result


def run_browser_command(cmd: str, timeout: int = 30) -> str:
    """Run an agent-browser command and return output."""
    try:
        result = subprocess.run(
            f"agent-browser {cmd}",
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return ""


def extract_results_from_snapshot(snapshot: str) -> list[FlightAvailability]:
    """Extract flight availability results from page snapshot text."""
    flights = []
    
    # Parse the accessibility tree/snapshot for table data
    # Look for patterns like: AF995, JNB, CDG, departure time, availability string
    
    # Split into lines and look for flight patterns
    lines = snapshot.split('\n')
    
    for line in lines:
        # Look for flight number pattern followed by availability codes
        match = re.search(
            r'([A-Z]{2}\d+)\s+.*?'  # Flight number
            r'([A-Z]{3})\s*[→\->]\s*([A-Z]{3})\s+.*?'  # Route
            r'(\d{1,2}[:/]\d{2}\s*[AP]M)\s+.*?'  # Departure time
            r'([A-Z]\d(?:[A-Z]\d)+)',  # Availability string
            line, re.IGNORECASE
        )
        
        if match:
            flight_num, origin, dest, depart_time, avail_str = match.groups()
            flights.append(FlightAvailability(
                flight=flight_num.upper(),
                origin=origin.upper(),
                destination=dest.upper(),
                depart=depart_time,
                arrive="",
                aircraft="",
                frequency="",
                availability=parse_availability_string(avail_str.upper())
            ))
    
    return flights


def extract_results_from_page() -> list[FlightAvailability]:
    """Extract flight availability results from current page via JS."""
    js_code = '''
    const results = [];
    document.querySelectorAll('table tbody tr').forEach(tr => {
        const cells = Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim());
        if (cells.length >= 7 && cells[0].match(/[A-Z]{2}\\d+/)) {
            results.push({
                flight: cells[0],
                stops: cells[1],
                depart: cells[2],
                arrive: cells[3],
                aircraft: cells[4],
                frequency: cells[5],
                availability: cells[6]
            });
        }
    });
    JSON.stringify(results);
    '''
    
    output = run_browser_command(f"eval '{js_code}'")
    
    try:
        # Clean up the output and parse JSON
        cleaned = output.strip()
        # Handle various output formats
        if cleaned.startswith('"') and cleaned.endswith('"'):
            cleaned = cleaned[1:-1]
        cleaned = cleaned.replace('\\n', '').replace('\\"', '"')
        
        data = json.loads(cleaned)
        
        flights = []
        for row in data:
            flights.append(FlightAvailability(
                flight=row['flight'].replace('(', ' ('),
                origin="",  # Will be extracted from depart field
                destination="",
                depart=row['depart'],
                arrive=row['arrive'],
                aircraft=row['aircraft'],
                frequency=row['frequency'],
                availability=parse_availability_string(row['availability']),
                stops=int(row['stops']) if row['stops'].isdigit() else 0
            ))
        
        return flights
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing results: {e}", file=sys.stderr)
        return []


def format_availability_compact(avail: dict) -> str:
    """Format availability dict as compact string."""
    parts = []
    
    # Business classes
    biz = ' '.join(f"{c}{avail.get(c, 0)}" for c in ['J', 'C', 'D', 'I', 'Z'] if c in avail)
    if biz:
        parts.append(f"J: {biz}")
    
    # Premium economy
    prem = ' '.join(f"{c}{avail.get(c, 0)}" for c in ['O', 'W'] if c in avail)
    if prem:
        parts.append(f"W: {prem}")
    
    # Economy
    econ = ' '.join(f"{c}{avail.get(c, 0)}" for c in ['Y', 'B', 'M'] if c in avail)
    if econ:
        parts.append(f"Y: {econ}")
    
    return " │ ".join(parts)


def print_fare_table(avail: dict, classes: Optional[list[str]] = None, mobile: bool = True):
    """Print detailed fare class table.
    
    Args:
        avail: Dict of fare class -> seat count
        classes: List of fare classes to show
        mobile: Use mobile-friendly stacked list format (default True)
    """
    # Default to key fare classes if not specified
    if classes is None:
        classes = ['J', 'C', 'D', 'I', 'Z', 'Y', 'B', 'M']
    
    if mobile:
        # Mobile-friendly stacked list format
        business = ['J', 'C', 'D', 'I', 'Z']
        economy = ['Y', 'B', 'M']
        
        # Business class section
        biz_fares = [c for c in business if c in avail and c in classes]
        if biz_fares:
            print("\nBusiness:")
            for cls in biz_fares:
                seats = avail[cls]
                _, desc = FARE_CLASSES.get(cls, ("?", "Unknown"))
                # Shorten description for mobile
                short_desc = desc.split("—")[-1].strip() if "—" in desc else desc
                print(f"• {cls} ({seats}) {short_desc}")
        
        # Economy class section
        eco_fares = [c for c in economy if c in avail and c in classes]
        if eco_fares:
            print("\nEconomy:")
            for cls in eco_fares:
                seats = avail[cls]
                _, desc = FARE_CLASSES.get(cls, ("?", "Unknown"))
                short_desc = desc.split("—")[-1].strip() if "—" in desc else desc
                print(f"• {cls} ({seats}) {short_desc}")
        
        print()  # Trailing newline
    else:
        # ASCII box table for terminal
        desc_width = 45
        
        print(f"┌───────┬───────┬{'─' * desc_width}┐")
        print(f"│ Class │ Seats │ {'Description':<{desc_width-1}}│")
        print(f"├───────┼───────┼{'─' * desc_width}┤")
        
        for cls in classes:
            if cls in avail:
                seats = avail[cls]
                cabin, desc = FARE_CLASSES.get(cls, ("?", "Unknown"))
                # Truncate description if needed
                if len(desc) > desc_width - 1:
                    desc = desc[:desc_width-4] + "..."
                print(f"│   {cls}   │   {seats}   │ {desc:<{desc_width-1}}│")
        
        print(f"└───────┴───────┴{'─' * desc_width}┘")


def print_flight_results(
    flights: list[FlightAvailability], 
    cabin: Optional[str] = None,
    detailed: bool = False,
    fare_classes: Optional[list[str]] = None,
    mobile: bool = True,
):
    """Print flight results.
    
    Args:
        flights: List of flight availability results
        cabin: Filter by cabin class (J, Y, W)
        detailed: Show detailed fare breakdown
        fare_classes: List of fare classes to display
        mobile: Use mobile-friendly format (default True)
    """
    if not flights:
        print("No flights found.")
        return
    
    if detailed and fare_classes:
        # Print detailed fare breakdown for each flight
        for f in flights:
            # Filter by cabin if specified
            if cabin == 'J' and f.business_seats() == 0:
                continue
            if cabin == 'Y' and f.economy_seats() == 0:
                continue
            
            route = f"{f.origin}→{f.destination}" if f.origin else ""
            aircraft = f" ({f.aircraft})" if f.aircraft else ""
            print(f"\n✈ {f.flight} {route} {f.depart}{aircraft}")
            print_fare_table(f.availability, fare_classes, mobile=mobile)
    else:
        # Compact view
        if mobile:
            # Mobile-friendly compact
            for f in flights:
                if cabin == 'J' and f.business_seats() == 0:
                    continue
                if cabin == 'Y' and f.economy_seats() == 0:
                    continue
                
                route = f"{f.origin}→{f.destination}" if f.origin else ""
                print(f"\n✈ {f.flight} {route} {f.depart}")
                
                # Inline availability
                biz = ' '.join(f"{c}{f.availability.get(c, 0)}" for c in ['J', 'C', 'D', 'I', 'Z'] if c in f.availability)
                eco = ' '.join(f"{c}{f.availability.get(c, 0)}" for c in ['Y', 'B', 'M'] if c in f.availability)
                
                if biz:
                    print(f"Biz: {biz}")
                if eco:
                    print(f"Eco: {eco}")
            print()
        else:
            # Terminal ASCII table
            print(f"\n{'─' * 80}")
            print(f"{'Flight':<15} {'Route':<12} {'Depart':<18} {'Aircraft':<8} {'Availability'}")
            print(f"{'─' * 80}")
            
            for f in flights:
                if cabin == 'J' and f.business_seats() == 0:
                    continue
                if cabin == 'Y' and f.economy_seats() == 0:
                    continue
                
                route = f"{f.origin}→{f.destination}" if f.origin else ""
                avail_str = format_availability_compact(f.availability)
                
                print(f"{f.flight:<15} {route:<12} {f.depart[:18]:<18} {f.aircraft:<8} {avail_str}")
            
            print(f"{'─' * 80}\n")


def search_and_display(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
    cabin: Optional[str] = None,
    detailed: bool = True,
    fare_classes: Optional[list[str]] = None,
    mobile: bool = True,
):
    """
    Full search flow: login, navigate, search, parse, display.
    
    Args:
        origin: 3-letter origin airport code
        destination: 3-letter destination airport code
        date: YYYY-MM-DD format
        airline: Optional 2-letter airline filter
        cabin: Filter cabin (J=business, Y=economy)
        detailed: Show detailed fare table
        fare_classes: List of fare classes to show (default: J,C,D,I,Z,Y,B,M)
        mobile: Use mobile-friendly format (default True)
    """
    from .browser import search_availability
    
    print(f"🔍 Searching ExpertFlyer: {origin} → {destination} on {date}", file=sys.stderr)
    
    if fare_classes is None:
        fare_classes = ['J', 'C', 'D', 'I', 'Z', 'Y', 'B', 'M']
    
    try:
        # Run the browser automation
        snapshot = search_availability(origin, destination, date, airline)
        
        # Try JS extraction first (more reliable)
        flights = extract_results_from_page()
        
        # Fall back to snapshot parsing
        if not flights:
            flights = extract_results_from_snapshot(snapshot)
        
        if not flights:
            print("❌ No results found. Check if the search completed.", file=sys.stderr)
            return
        
        print_flight_results(
            flights, 
            cabin=cabin, 
            detailed=detailed,
            fare_classes=fare_classes,
            mobile=mobile,
        )
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        raise


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="ExpertFlyer seat availability scraper")
    subparsers = parser.add_subparsers(dest="command")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search for availability")
    search_parser.add_argument("origin", help="Origin airport code")
    search_parser.add_argument("destination", help="Destination airport code")
    search_parser.add_argument("date", help="Date (YYYY-MM-DD)")
    search_parser.add_argument("-a", "--airline", help="Airline filter (2-letter code)")
    search_parser.add_argument("-c", "--cabin", choices=['J', 'Y', 'W'], help="Cabin filter")
    search_parser.add_argument("-f", "--fares", help="Fare classes to show (comma-separated)")
    search_parser.add_argument("--compact", action="store_true", help="Compact output")
    
    # Extract command (from current page)
    extract_parser = subparsers.add_parser("extract", help="Extract from current page")
    extract_parser.add_argument("-c", "--cabin", choices=['J', 'Y', 'W'], help="Cabin filter")
    extract_parser.add_argument("-f", "--fares", help="Fare classes to show")
    
    args = parser.parse_args()
    
    if args.command == "search":
        fare_classes = args.fares.split(",") if args.fares else None
        search_and_display(
            args.origin,
            args.destination,
            args.date,
            airline=args.airline,
            cabin=args.cabin,
            detailed=not args.compact,
            fare_classes=fare_classes,
        )
    
    elif args.command == "extract":
        print("Extracting results from current ExpertFlyer page...")
        flights = extract_results_from_page()
        fare_classes = args.fares.split(",") if args.fares else None
        print_flight_results(
            flights,
            cabin=args.cabin,
            detailed=True,
            fare_classes=fare_classes,
        )
    
    else:
        parser.print_help()
