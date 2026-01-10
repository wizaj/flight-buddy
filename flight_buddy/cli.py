"""Flight Buddy CLI."""

import re
import sys
from datetime import date, timedelta
from typing import Optional

import click

from .client import AmadeusClient, AmadeusError
from .models import (
    parse_flight_offers,
    parse_flight_schedule,
    parse_flight_availability,
)
from .formatter import (
    print_search_results,
    print_flight_schedule,
    print_availability,
    print_error,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

CABIN_MAP = {
    "economy": "ECONOMY",
    "eco": "ECONOMY",
    "y": "ECONOMY",
    "premium": "PREMIUM_ECONOMY",
    "pey": "PREMIUM_ECONOMY",
    "w": "PREMIUM_ECONOMY",
    "business": "BUSINESS",
    "biz": "BUSINESS",
    "j": "BUSINESS",
    "first": "FIRST",
    "f": "FIRST",
}


def parse_cabin(cabin: Optional[str]) -> Optional[str]:
    """Parse cabin class shortcut to Amadeus value."""
    if not cabin:
        return None
    return CABIN_MAP.get(cabin.lower(), cabin.upper())


def parse_date(date_str: str) -> str:
    """Parse date string, supporting 'today', 'tomorrow', etc."""
    if date_str.lower() == "today":
        return date.today().isoformat()
    elif date_str.lower() == "tomorrow":
        return (date.today() + timedelta(days=1)).isoformat()
    # Assume YYYY-MM-DD format
    return date_str


def parse_flight_number(flight: str) -> tuple[str, str]:
    """
    Parse flight number into carrier and number.
    
    Examples:
        EK766 → ("EK", "766")
        QR1369 → ("QR", "1369")
    """
    match = re.match(r"^([A-Za-z]{2})(\d+)$", flight.strip())
    if not match:
        raise click.BadParameter(f"Invalid flight number: {flight}. Expected format: EK766")
    return match.group(1).upper(), match.group(2)


# ─────────────────────────────────────────────────────────────
# CLI App
# ─────────────────────────────────────────────────────────────

@click.group()
@click.version_option(package_name="flight-buddy")
def cli():
    """✈ Flight Buddy - Quick flight lookups from the command line."""
    pass


# ─────────────────────────────────────────────────────────────
# search command
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("origin")
@click.argument("destination")
@click.argument("date")
@click.option("-c", "--cabin", help="Cabin class (economy/Y, premium/W, business/J, first/F)")
@click.option("-a", "--adults", default=1, help="Number of adults (1-9)")
@click.option("-d", "--direct", is_flag=True, help="Direct flights only")
@click.option("-A", "--airline", help="Include airlines (comma-separated IATA codes)")
@click.option("-X", "--exclude", help="Exclude airlines (comma-separated)")
@click.option("-m", "--max", "max_results", default=10, help="Max results")
@click.option("--currency", default="USD", help="Currency code")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def search(
    origin: str,
    destination: str,
    date: str,
    cabin: Optional[str],
    adults: int,
    direct: bool,
    airline: Optional[str],
    exclude: Optional[str],
    max_results: int,
    currency: str,
    as_json: bool,
):
    """Search for flights on a route.
    
    Examples:
    
        fb search JNB DXB 2026-02-01
        
        fb search JNB DXB tomorrow --cabin business
        
        fb search JNB DXB 2026-02-01 -c J -d --airline EK,QR
    """
    try:
        parsed_date = parse_date(date)
        parsed_cabin = parse_cabin(cabin)
        airlines = [a.strip().upper() for a in airline.split(",")] if airline else None
        exclude_airlines = [a.strip().upper() for a in exclude.split(",")] if exclude else None
        
        with AmadeusClient() as client:
            response = client.search_flights(
                origin=origin,
                destination=destination,
                departure_date=parsed_date,
                adults=adults,
                cabin=parsed_cabin,
                non_stop=direct,
                airlines=airlines,
                exclude_airlines=exclude_airlines,
                max_results=max_results,
                currency=currency,
            )
        
        offers = parse_flight_offers(response)
        print_search_results(
            offers,
            origin=origin.upper(),
            destination=destination.upper(),
            date=parsed_date,
            cabin=parsed_cabin,
            adults=adults,
            as_json=as_json,
        )
        
    except AmadeusError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# flight command
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("flight_number")
@click.argument("date", default="today")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def flight(flight_number: str, date: str, as_json: bool):
    """Look up a flight by number.
    
    Examples:
    
        fb flight EK766
        
        fb flight EK766 today
        
        fb flight QR1369 2026-02-01
    """
    try:
        carrier, number = parse_flight_number(flight_number)
        parsed_date = parse_date(date)
        
        with AmadeusClient() as client:
            response = client.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
        
        schedules = parse_flight_schedule(response)
        print_flight_schedule(
            schedules,
            flight_code=flight_number.upper(),
            date=parsed_date,
            as_json=as_json,
        )
        
    except AmadeusError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# avail command
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("flight_number")
@click.argument("date", default="today")
@click.option("-c", "--cabin", help="Filter cabin class")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def avail(flight_number: str, date: str, cabin: Optional[str], as_json: bool):
    """Check seat availability by cabin class.
    
    Examples:
    
        fb avail EK766 today
        
        fb avail EK766 tomorrow --cabin J
        
        fb avail QR1369 2026-02-01 -c business
    """
    try:
        carrier, number = parse_flight_number(flight_number)
        parsed_date = parse_date(date)
        cabin_filter = parse_cabin(cabin)
        
        # First get flight schedule to know origin/destination
        with AmadeusClient() as client:
            # Get schedule first
            sched_response = client.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
            schedules = parse_flight_schedule(sched_response)
            
            if not schedules:
                print_error(f"Flight {flight_number.upper()} not found on {parsed_date}")
                sys.exit(1)
            
            sched = schedules[0]
            
            # Get availability
            avail_response = client.get_flight_availability(
                origin=sched.departure.code,
                destination=sched.arrival.code,
                departure_date=parsed_date,
                carrier_code=carrier,
                flight_number=number,
            )
        
        availabilities = parse_flight_availability(avail_response)
        
        # Filter to just the requested flight
        target_flight = f"{carrier}{number}"
        filtered = [a for a in availabilities if a.flight_code == target_flight]
        
        if not filtered and availabilities:
            # Try partial match (sandbox sometimes returns different codes)
            filtered = [a for a in availabilities if number in a.flight_number]
        
        print_availability(
            filtered if filtered else availabilities[:1],  # Show at least one result
            flight_code=flight_number.upper(),
            date=parsed_date,
            cabin_filter=cabin_filter,
            as_json=as_json,
        )
        
    except AmadeusError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# seats command
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("flight_number")
@click.argument("date", default="today")
@click.option("-c", "--cabin", help="Filter cabin class")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def seats(flight_number: str, date: str, cabin: Optional[str], as_json: bool):
    """Show seat map for a flight.
    
    Examples:
    
        fb seats EK766 today
        
        fb seats EK766 --cabin business
    """
    try:
        carrier, number = parse_flight_number(flight_number)
        parsed_date = parse_date(date)
        cabin_filter = parse_cabin(cabin)
        
        with AmadeusClient() as client:
            # Search for this specific flight to get offer
            # We need origin/destination first from schedule
            sched_response = client.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
            schedules = parse_flight_schedule(sched_response)
            
            if not schedules:
                print_error(f"Flight {flight_number.upper()} not found on {parsed_date}")
                sys.exit(1)
            
            sched = schedules[0]
            
            # Search for flight offers on this route
            search_response = client.search_flights(
                origin=sched.departure.code,
                destination=sched.arrival.code,
                departure_date=parsed_date,
                max_results=50,  # Get more to find our flight
            )
            
            offers = parse_flight_offers(search_response)
            
            # Find offer matching our flight
            target_flight = f"{carrier}{number}"
            matching_offer = None
            for offer in offers:
                for seg in offer.outbound.segments:
                    if seg.flight_code == target_flight:
                        matching_offer = offer
                        break
                if matching_offer:
                    break
            
            if not matching_offer:
                print_error(f"Could not find bookable offer for {target_flight}")
                sys.exit(1)
            
            # Get seat map
            seatmap_response = client.get_seat_map(matching_offer.raw)
        
        # Parse and display seat map
        # Note: Seat map parsing is complex, showing simplified message for now
        from rich.console import Console
        console = Console()
        console.print(f"\n✈  [bold]{flight_number.upper()}[/bold]  ·  {sched.departure.code} → {sched.arrival.code}  ·  {parsed_date}")
        console.print(f"\n[yellow]Seat map data retrieved. Full visualization coming in Phase 3.[/yellow]")
        console.print(f"[dim]Raw response has {len(seatmap_response.get('data', []))} deck(s)[/dim]\n")
        
    except AmadeusError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
