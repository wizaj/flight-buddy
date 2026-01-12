"""Flight Buddy CLI."""

import re
import sys
from datetime import date, timedelta
from typing import Optional

import click

from .providers import get_provider, ProviderError
from .formatter import (
    print_search_results,
    print_flight_schedule,
    print_availability,
    print_seat_map,
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
@click.option("-p", "--provider", envvar="FLIGHT_BUDDY_PROVIDER", 
              help="Provider (amadeus/duffel). Default from config.yaml")
@click.pass_context
def cli(ctx, provider: Optional[str]):
    """✈ Flight Buddy - Quick flight lookups from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider


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
@click.pass_context
def search(
    ctx,
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
        
        with get_provider(ctx.obj.get("provider")) as provider:
            offers = provider.search_flights(
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
        
        print_search_results(
            offers,
            origin=origin.upper(),
            destination=destination.upper(),
            date=parsed_date,
            cabin=parsed_cabin,
            adults=adults,
            as_json=as_json,
        )
        
    except ProviderError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# flight command
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("flight_number")
@click.argument("date", default="today")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
@click.pass_context
def flight(ctx, flight_number: str, date: str, as_json: bool):
    """Look up a flight by number.
    
    Examples:
    
        fb flight EK766
        
        fb flight EK766 today
        
        fb flight QR1369 2026-02-01
    """
    try:
        carrier, number = parse_flight_number(flight_number)
        parsed_date = parse_date(date)
        
        with get_provider(ctx.obj.get("provider")) as provider:
            schedules = provider.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
        
        print_flight_schedule(
            schedules,
            flight_code=flight_number.upper(),
            date=parsed_date,
            as_json=as_json,
        )
        
    except ProviderError as e:
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
@click.pass_context
def avail(ctx, flight_number: str, date: str, cabin: Optional[str], as_json: bool):
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
        with get_provider(ctx.obj.get("provider")) as provider:
            # Get schedule first
            schedules = provider.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
            
            if not schedules:
                print_error(f"Flight {flight_number.upper()} not found on {parsed_date}")
                sys.exit(1)
            
            sched = schedules[0]
            
            # Get availability
            availabilities = provider.get_flight_availability(
                origin=sched.departure.code,
                destination=sched.arrival.code,
                departure_date=parsed_date,
                carrier_code=carrier,
                flight_number=number,
            )
        
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
        
    except ProviderError as e:
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
@click.pass_context
def seats(ctx, flight_number: str, date: str, cabin: Optional[str], as_json: bool):
    """Show seat map for a flight.
    
    Examples:
    
        fb seats EK766 today
        
        fb seats EK766 --cabin business
    """
    try:
        carrier, number = parse_flight_number(flight_number)
        parsed_date = parse_date(date)
        cabin_filter = parse_cabin(cabin)
        
        with get_provider(ctx.obj.get("provider")) as provider:
            # Get schedule to find origin/destination
            schedules = provider.get_flight_schedule(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
            )
            
            if not schedules:
                print_error(f"Flight {flight_number.upper()} not found on {parsed_date}")
                sys.exit(1)
            
            sched = schedules[0]
            
            # Get seat map
            seat_map = provider.get_seat_map(
                carrier_code=carrier,
                flight_number=number,
                departure_date=parsed_date,
                origin=sched.departure.code,
                destination=sched.arrival.code,
            )
        
        if not seat_map:
            print_error(f"No seat map data for {flight_number.upper()}")
            sys.exit(1)
        
        print_seat_map(seat_map, cabin_filter=cabin_filter, as_json=as_json)
        
    except ProviderError as e:
        print_error(str(e), e.details)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
