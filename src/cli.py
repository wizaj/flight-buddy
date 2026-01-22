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
@click.option("-r", "--return", "return_date", help="Return date (for round-trip)")
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
    return_date: Optional[str],
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
        
        fb search JNB DXB 2026-02-01 --return 2026-02-08
        
        fb search JNB DXB tomorrow --cabin business
        
        fb search JNB DXB 2026-02-01 -c J -d --airline EK,QR
    """
    try:
        parsed_date = parse_date(date)
        parsed_return = parse_date(return_date) if return_date else None
        parsed_cabin = parse_cabin(cabin)
        airlines = [a.strip().upper() for a in airline.split(",")] if airline else None
        exclude_airlines = [a.strip().upper() for a in exclude.split(",")] if exclude else None
        
        with get_provider(ctx.obj.get("provider")) as provider:
            offers = provider.search_flights(
                origin=origin,
                destination=destination,
                departure_date=parsed_date,
                return_date=parsed_return,
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
            return_date=parsed_return,
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
# awards command (Seats.aero)
# ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("origin")
@click.argument("destination")
@click.argument("date")
@click.option("-e", "--end-date", help="End date for date range search")
@click.option("-c", "--cabin", help="Filter cabin class (Y, W, J, F)")
@click.option("-s", "--source", "--program", help="Mileage programs (comma-separated: aeroplan,united,american)")
@click.option("-A", "--airline", help="Operating airlines (comma-separated IATA codes)")
@click.option("-d", "--direct", is_flag=True, help="Direct flights only")
@click.option("--cheapest", is_flag=True, help="Sort by lowest mileage cost")
@click.option("-m", "--max", "max_results", default=20, help="Max results")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def awards(
    origin: str,
    destination: str,
    date: str,
    end_date: Optional[str],
    cabin: Optional[str],
    source: Optional[str],
    airline: Optional[str],
    direct: bool,
    cheapest: bool,
    max_results: int,
    as_json: bool,
):
    """Search award flight availability (miles/points).
    
    Uses Seats.aero to find award redemption availability across
    multiple mileage programs (Aeroplan, United, American, etc.).
    
    Examples:
    
        fb awards JNB DXB 2026-02-14
        
        fb awards JNB DXB 2026-02-14 --cabin J
        
        fb awards JNB DXB 2026-02-14 --program aeroplan,united
        
        fb awards JNB DXB 2026-02-14 -e 2026-02-21 --cheapest
        
        fb awards JNB DXB tomorrow --direct --cabin business
    """
    from .providers import get_award_provider
    from .providers.seatsaero.adapter import format_mileage, format_program_name, CABIN_NAMES
    
    try:
        parsed_date = parse_date(date)
        parsed_end = parse_date(end_date) if end_date else None
        
        # Parse cabin filter
        cabins = None
        if cabin:
            cabins = [c.strip().upper() for c in cabin.split(",")]
        
        # Parse sources
        sources = None
        if source:
            sources = [s.strip().lower() for s in source.split(",")]
        
        # Parse carriers
        carriers = None
        if airline:
            carriers = [a.strip().upper() for a in airline.split(",")]
        
        with get_award_provider() as provider:
            response = provider.search_awards(
                origin=origin,
                destination=destination,
                start_date=parsed_date,
                end_date=parsed_end,
                cabins=cabins,
                sources=sources,
                carriers=carriers,
                direct_only=direct,
                order_by="lowest_mileage" if cheapest else None,
                take=max_results,
            )
        
        if as_json:
            import json
            output = {
                "origin": origin.upper(),
                "destination": destination.upper(),
                "date": parsed_date,
                "end_date": parsed_end,
                "count": response.count,
                "results": [
                    {
                        "date": r.date,
                        "source": r.source,
                        "source_name": format_program_name(r.source),
                        "origin": r.origin,
                        "destination": r.destination,
                        "cabins": {
                            cabin: {
                                "available": data.available,
                                "mileage_cost": data.mileage_cost,
                                "airlines": data.airlines,
                                "direct": data.direct,
                            }
                            for cabin, data in r.cabins.items()
                        }
                    }
                    for r in response.results
                ]
            }
            click.echo(json.dumps(output, indent=2))
            return
        
        # Pretty print
        click.echo()
        click.secho(f"✈  {origin.upper()} → {destination.upper()}", fg="cyan", bold=True, nl=False)
        click.echo(f"  •  Award Search  •  ", nl=False)
        if parsed_end and parsed_end != parsed_date:
            click.echo(f"{parsed_date} to {parsed_end}")
        else:
            click.echo(parsed_date)
        click.echo()
        
        if not response.results:
            click.secho("  No award availability found.", fg="yellow")
            click.echo()
            return
        
        # Group by date for cleaner output
        from itertools import groupby
        
        for result_date, date_results in groupby(response.results, key=lambda r: r.date):
            date_results = list(date_results)
            click.secho(f"  {result_date}", fg="white", bold=True)
            click.secho("  " + "─" * 60, fg="bright_black")
            
            for r in date_results:
                # Show each program's availability
                program = format_program_name(r.source)
                
                # Check affordability
                from .balances import check_affordability
                
                # Find best available cabin
                avail_cabins = []
                for cab in ["F", "J", "W", "Y"]:
                    data = r.cabins.get(cab)
                    if data and data.available:
                        cost = format_mileage(data.mileage_cost)
                        direct_mark = "✓" if data.direct else ""
                        
                        # Check if affordable
                        afford = check_affordability(r.source, data.mileage_cost)
                        if afford["balance"] > 0:  # Only show if we track this program
                            if afford["status"] == "ok":
                                afford_mark = "💰"
                            elif afford["status"] == "close":
                                afford_mark = "⚠️"
                            else:
                                afford_mark = ""
                        else:
                            afford_mark = ""
                        
                        avail_cabins.append(f"{CABIN_NAMES.get(cab, cab)[0]}: {cost} {direct_mark}{afford_mark}")
                
                if avail_cabins:
                    cabins_str = "  |  ".join(avail_cabins)
                    click.echo(f"    {program:24} {cabins_str}")
            
            click.echo()
        
        if response.has_more:
            click.secho(f"  ... more results available (use --max to increase)", fg="bright_black")
            click.echo()
        
    except ProviderError as e:
        print_error(str(e), getattr(e, "details", []))
        sys.exit(1)
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


# ─────────────────────────────────────────────────────────────
# balance command
# ─────────────────────────────────────────────────────────────

@cli.group(invoke_without_command=True)
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
@click.pass_context
def balance(ctx, as_json: bool):
    """View and manage mileage balances.
    
    Examples:
    
        fb balance                     # Show all balances
        
        fb balance update emirates 145000
        
        fb balance update united 82000 --tier Gold
        
        fb balance history emirates
    """
    if ctx.invoked_subcommand is not None:
        return
    
    # Show all balances
    from .balances import get_all_balances, format_miles, format_delta, PROGRAM_NAMES
    
    balances = get_all_balances()
    
    if as_json:
        import json
        click.echo(json.dumps(balances, indent=2, default=str))
        return
    
    if not balances:
        click.echo()
        click.secho("  No balances tracked yet.", fg="yellow")
        click.echo("  Use: fb balance update <program> <miles>")
        click.echo()
        return
    
    click.echo()
    click.secho("  ✈  Mileage Balances", fg="cyan", bold=True)
    click.secho("  " + "─" * 50, fg="bright_black")
    
    total_value = 0  # Rough estimate at ~1 cent/mile
    
    for key, data in sorted(balances.items(), key=lambda x: x[1].get("miles", 0), reverse=True):
        program = data.get("program", PROGRAM_NAMES.get(key, key.title()))
        miles = data.get("miles", 0)
        tier = data.get("tier", "")
        updated = data.get("updated", "")
        
        # Check for recent delta
        history = data.get("history", [])
        delta_str = ""
        if len(history) >= 2:
            last_delta = history[-1].get("delta")
            if last_delta:
                delta_str = f" ({format_delta(last_delta)})"
        
        tier_str = f" [{tier}]" if tier else ""
        
        click.echo(f"    {program:24} ", nl=False)
        click.secho(f"{format_miles(miles):>12}", fg="green", bold=True, nl=False)
        click.secho(f"{delta_str}", fg="cyan" if delta_str.startswith(" (+") else "red", nl=False)
        click.secho(f"{tier_str}", fg="bright_black")
        
        total_value += miles
    
    click.echo()
    click.secho(f"    {'Total':24} {format_miles(total_value):>12}", fg="white", bold=True)
    click.secho(f"    {'Est. value':24} ${total_value * 0.01:>11,.0f}", fg="bright_black")
    click.echo()


@balance.command("update")
@click.argument("program")
@click.argument("miles", type=int)
@click.option("-t", "--tier", help="Status tier (e.g., Gold, Platinum)")
@click.option("-n", "--note", help="Note for this update")
def balance_update(program: str, miles: int, tier: Optional[str], note: Optional[str]):
    """Update balance for a mileage program.
    
    Examples:
    
        fb balance update emirates 145000
        
        fb balance update united 82000 --tier Gold
        
        fb balance update delta 50000 --note "After LAX trip"
    """
    from .balances import update_balance, format_miles, format_delta, PROGRAM_NAMES
    
    entry = update_balance(program, miles, tier=tier, note=note)
    
    program_name = entry.get("program", PROGRAM_NAMES.get(program.lower(), program.title()))
    
    # Show delta if not first entry
    history = entry.get("history", [])
    delta_str = ""
    if len(history) >= 2 and history[-1].get("delta"):
        delta = history[-1]["delta"]
        delta_str = f" ({format_delta(delta)})"
        
    click.echo()
    click.secho(f"  ✓ Updated {program_name}", fg="green", bold=True)
    click.echo(f"    Balance: {format_miles(miles)}{delta_str}")
    if tier:
        click.echo(f"    Tier: {tier}")
    click.echo()


@balance.command("history")
@click.argument("program")
@click.option("-n", "--limit", default=10, help="Number of entries to show")
@click.option("-j", "--json", "as_json", is_flag=True, help="JSON output")
def balance_history(program: str, limit: int, as_json: bool):
    """Show balance history for a program.
    
    Examples:
    
        fb balance history emirates
        
        fb balance history united --limit 20
    """
    from .balances import get_balance, format_miles, format_delta, PROGRAM_NAMES
    
    data = get_balance(program)
    
    if not data:
        click.secho(f"  No balance found for '{program}'", fg="yellow")
        return
    
    history = data.get("history", [])
    
    if as_json:
        import json
        click.echo(json.dumps(history[-limit:], indent=2, default=str))
        return
    
    program_name = data.get("program", PROGRAM_NAMES.get(program.lower(), program.title()))
    
    click.echo()
    click.secho(f"  ✈  {program_name} History", fg="cyan", bold=True)
    click.secho("  " + "─" * 50, fg="bright_black")
    
    for entry in reversed(history[-limit:]):
        date_str = entry.get("date", "")
        miles = entry.get("miles", 0)
        delta = entry.get("delta")
        note = entry.get("note", "")
        
        delta_str = f" ({format_delta(delta)})" if delta else ""
        note_str = f" - {note}" if note else ""
        
        color = "green" if delta and delta > 0 else ("red" if delta and delta < 0 else "white")
        
        click.echo(f"    {date_str}  ", nl=False)
        click.secho(f"{format_miles(miles):>12}", fg=color, nl=False)
        click.secho(delta_str, fg=color, nl=False)
        click.secho(note_str, fg="bright_black")
    
    click.echo()


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    cli()


if __name__ == "__main__":
    main()
