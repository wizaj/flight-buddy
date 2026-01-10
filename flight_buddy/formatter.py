"""Output formatting for Flight Buddy."""

import json
from datetime import datetime
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from .models import (
    FlightOffer,
    FlightSchedule,
    FlightAvailability,
    SeatMap,
    Seat,
)

console = Console()


def format_duration(iso_duration: str) -> str:
    """Convert ISO duration (PT8H30M) to human readable (8h30m)."""
    if not iso_duration:
        return ""
    return iso_duration.replace("PT", "").lower()


def format_time(dt: datetime) -> str:
    """Format time as HH:MM."""
    return dt.strftime("%H:%M")


def format_date(dt: datetime) -> str:
    """Format date as 'Sat 01 Feb 2026'."""
    return dt.strftime("%a %d %b %Y")


def day_diff(dep: datetime, arr: datetime) -> str:
    """Calculate day difference for overnight flights."""
    diff = (arr.date() - dep.date()).days
    if diff == 0:
        return ""
    elif diff > 0:
        return f"+{diff}"
    else:
        return str(diff)


# ─────────────────────────────────────────────────────────────
# Flight Search Output
# ─────────────────────────────────────────────────────────────

def print_search_results(
    offers: list[FlightOffer],
    origin: str,
    destination: str,
    date: str,
    cabin: Optional[str] = None,
    adults: int = 1,
    as_json: bool = False,
):
    """Print flight search results."""
    if as_json:
        print(json.dumps({
            "query": {
                "origin": origin,
                "destination": destination,
                "date": date,
                "cabin": cabin,
                "adults": adults,
            },
            "results": [_offer_to_dict(o) for o in offers],
        }, indent=2))
        return
    
    # Header
    cabin_str = f"  ·  {cabin}" if cabin else ""
    adults_str = f"{adults} adult{'s' if adults > 1 else ''}"
    console.print(f"\n✈  [bold]{origin} → {destination}[/bold]  ·  {date}  ·  {adults_str}{cabin_str}\n")
    
    if not offers:
        console.print("[yellow]No flights found[/yellow]")
        return
    
    for offer in offers:
        _print_offer(offer)
    
    console.print(f"\n[dim]{'─' * 50}[/dim]")
    console.print(f"[dim]Showing {len(offers)} results  ·  Prices include taxes[/dim]\n")


def _print_offer(offer: FlightOffer):
    """Print a single flight offer."""
    itin = offer.outbound
    
    # Build flight codes
    flights = " → ".join(seg.flight_code for seg in itin.segments)
    
    # Get carrier name from first segment
    carrier_name = itin.segments[0].carrier_name or itin.segments[0].carrier
    
    # Times
    dep_time = format_time(itin.departure_time)
    arr_time = format_time(itin.arrival_time)
    day_change = day_diff(itin.departure_time, itin.arrival_time)
    if day_change:
        arr_time = f"{arr_time} ({day_change})"
    
    # Duration and stops
    duration = format_duration(itin.duration)
    if itin.is_direct:
        stops_str = "Direct"
    else:
        stop_codes = [seg.arrival.code for seg in itin.segments[:-1]]
        stops_str = f"{itin.stops} stop{'s' if itin.stops > 1 else ''} {', '.join(stop_codes)}"
    
    # Cabin
    cabin = offer.cabin or "Economy"
    
    # Print
    console.print(f"[bold]{carrier_name}[/bold] [dim]{flights}[/dim]")
    console.print(f"  {dep_time} → {arr_time}  ·  {duration}  ·  {stops_str}")
    console.print(f"  {cabin}  ·  [green bold]{offer.price}[/green bold]")
    console.print()


def _offer_to_dict(offer: FlightOffer) -> dict:
    """Convert offer to JSON-serializable dict."""
    return {
        "price": {"amount": offer.price.amount, "currency": offer.price.currency},
        "itinerary": {
            "duration": offer.outbound.duration,
            "segments": [
                {
                    "flight": seg.flight_code,
                    "carrier": seg.carrier_name or seg.carrier,
                    "departure": {
                        "airport": seg.departure.code,
                        "time": seg.departure_time.isoformat(),
                    },
                    "arrival": {
                        "airport": seg.arrival.code,
                        "time": seg.arrival_time.isoformat(),
                    },
                    "duration": seg.duration,
                    "cabin": seg.cabin,
                }
                for seg in offer.outbound.segments
            ],
        },
    }


# ─────────────────────────────────────────────────────────────
# Flight Schedule Output
# ─────────────────────────────────────────────────────────────

def print_flight_schedule(
    schedules: list[FlightSchedule],
    flight_code: str,
    date: str,
    as_json: bool = False,
):
    """Print flight schedule."""
    if as_json:
        print(json.dumps({
            "query": {"flight": flight_code, "date": date},
            "results": [_schedule_to_dict(s) for s in schedules],
        }, indent=2))
        return
    
    if not schedules:
        console.print(f"\n[yellow]No schedule found for {flight_code} on {date}[/yellow]\n")
        return
    
    for sched in schedules:
        _print_schedule(sched, date)


def _print_schedule(sched: FlightSchedule, date: str):
    """Print a single flight schedule."""
    carrier_name = sched.carrier_name or sched.carrier
    
    dep_time = format_time(sched.departure_time)
    arr_time = format_time(sched.arrival_time)
    day_change = day_diff(sched.departure_time, sched.arrival_time)
    if day_change:
        arr_time = f"{arr_time}{day_change}"
    
    duration = format_duration(sched.duration)
    
    console.print(f"\n✈  [bold]{sched.flight_code}[/bold]  ·  {carrier_name}  ·  {date}\n")
    console.print(f"  [bold]{sched.departure.code}[/bold]  {dep_time}  {'─' * 20}  [bold]{sched.arrival.code}[/bold]  {arr_time}")
    
    # Details
    details = []
    if duration:
        details.append(f"Duration: {duration}")
    if sched.aircraft:
        details.append(f"Aircraft: {sched.aircraft}")
    if sched.status:
        details.append(f"Status: {sched.status}")
    
    if details:
        console.print(f"  [dim]{' · '.join(details)}[/dim]")
    console.print()


def _schedule_to_dict(sched: FlightSchedule) -> dict:
    """Convert schedule to JSON-serializable dict."""
    return {
        "flight": sched.flight_code,
        "carrier": sched.carrier_name or sched.carrier,
        "departure": {
            "airport": sched.departure.code,
            "terminal": sched.departure.terminal,
            "time": sched.departure_time.isoformat(),
        },
        "arrival": {
            "airport": sched.arrival.code,
            "terminal": sched.arrival.terminal,
            "time": sched.arrival_time.isoformat(),
        },
        "duration": sched.duration,
        "aircraft": sched.aircraft,
        "status": sched.status,
    }


# ─────────────────────────────────────────────────────────────
# Flight Availability Output
# ─────────────────────────────────────────────────────────────

def print_availability(
    availabilities: list[FlightAvailability],
    flight_code: str,
    date: str,
    cabin_filter: Optional[str] = None,
    as_json: bool = False,
):
    """Print cabin availability."""
    if as_json:
        print(json.dumps({
            "query": {"flight": flight_code, "date": date, "cabin": cabin_filter},
            "results": [_availability_to_dict(a) for a in availabilities],
        }, indent=2))
        return
    
    if not availabilities:
        console.print(f"\n[yellow]No availability found for {flight_code} on {date}[/yellow]\n")
        return
    
    for avail in availabilities:
        _print_availability(avail, date, cabin_filter)


def _print_availability(avail: FlightAvailability, date: str, cabin_filter: Optional[str] = None):
    """Print availability for a single flight."""
    console.print(f"\n✈  [bold]{avail.flight_code}[/bold]  ·  {avail.departure.code} → {avail.arrival.code}  ·  {date}\n")
    
    table = Table(show_header=True, header_style="bold", box=None)
    table.add_column("Cabin", style="dim")
    table.add_column("Class")
    table.add_column("Available", justify="right")
    
    cabin_filter_upper = cabin_filter.upper() if cabin_filter else None
    
    for cab in avail.cabins:
        # Check if this matches filter
        is_match = cabin_filter_upper and (
            cab.cabin == cabin_filter_upper or 
            cab.booking_class == cabin_filter_upper
        )
        
        avail_str = str(cab.available) if cab.available > 0 else "—"
        marker = " ←" if is_match else ""
        
        style = "green bold" if is_match else None
        table.add_row(
            cab.cabin.title(),
            cab.booking_class,
            f"{avail_str}{marker}",
            style=style,
        )
    
    console.print(table)
    console.print()


def _availability_to_dict(avail: FlightAvailability) -> dict:
    """Convert availability to JSON-serializable dict."""
    return {
        "flight": avail.flight_code,
        "departure": {"airport": avail.departure.code, "time": avail.departure_time.isoformat()},
        "arrival": {"airport": avail.arrival.code, "time": avail.arrival_time.isoformat()},
        "cabins": [
            {"cabin": c.cabin, "class": c.booking_class, "available": c.available}
            for c in avail.cabins
        ],
    }


# ─────────────────────────────────────────────────────────────
# Seat Map Output
# ─────────────────────────────────────────────────────────────

def print_seat_map(
    seat_map: SeatMap,
    cabin_filter: Optional[str] = None,
    as_json: bool = False,
):
    """Print seat map."""
    if as_json:
        print(json.dumps(_seat_map_to_dict(seat_map, cabin_filter), indent=2))
        return
    
    console.print(f"\n✈  [bold]{seat_map.flight_code}[/bold]  ·  {seat_map.departure.code} → {seat_map.arrival.code}")
    
    cabin_name = cabin_filter.title() if cabin_filter else "All"
    console.print(f"   {cabin_name} Class\n")
    
    seats = seat_map.seats_by_cabin(cabin_filter) if cabin_filter else [s for d in seat_map.decks for s in d]
    
    if not seats:
        console.print("[yellow]No seats found for this cabin[/yellow]\n")
        return
    
    # Group by row
    rows: dict[int, list[Seat]] = {}
    columns: set[str] = set()
    for seat in seats:
        row = seat.row
        if row not in rows:
            rows[row] = []
        rows[row].append(seat)
        columns.add(seat.column)
    
    # Sort columns
    sorted_cols = sorted(columns)
    
    # Print header
    header = "      " + "   ".join(f" {c} " for c in sorted_cols)
    console.print(f"[dim]{header}[/dim]")
    console.print(f"   ╔{'═' * (len(sorted_cols) * 5 + 2)}╗")
    
    # Print rows
    for row_num in sorted(rows.keys()):
        row_seats = {s.column: s for s in rows[row_num]}
        row_str = f"  {row_num:2d} ║ "
        
        for col in sorted_cols:
            seat = row_seats.get(col)
            if seat:
                if seat.available:
                    row_str += " [green]✓[/green] "
                else:
                    row_str += " [red]✗[/red] "
            else:
                row_str += "   "
            row_str += " "
        
        row_str += "║"
        console.print(row_str)
    
    console.print(f"   ╚{'═' * (len(sorted_cols) * 5 + 2)}╝")
    
    # Legend
    available = seat_map.available_count(cabin_filter)
    total = len(seats)
    console.print(f"\n  [green]✓[/green] available  [red]✗[/red] occupied")
    console.print(f"  {available} of {total} seats available\n")


def _seat_map_to_dict(seat_map: SeatMap, cabin_filter: Optional[str] = None) -> dict:
    """Convert seat map to JSON-serializable dict."""
    seats = seat_map.seats_by_cabin(cabin_filter) if cabin_filter else [s for d in seat_map.decks for s in d]
    
    return {
        "flight": seat_map.flight_code,
        "aircraft": seat_map.aircraft,
        "departure": seat_map.departure.code,
        "arrival": seat_map.arrival.code,
        "date": seat_map.departure_date,
        "seats": [
            {
                "number": s.number,
                "available": s.available,
                "cabin": s.cabin,
                "characteristics": s.characteristics,
            }
            for s in seats
        ],
        "available_count": seat_map.available_count(cabin_filter),
        "total_count": len(seats),
    }


# ─────────────────────────────────────────────────────────────
# Errors
# ─────────────────────────────────────────────────────────────

def print_error(message: str, details: Optional[list] = None):
    """Print error message."""
    console.print(f"\n[red bold]Error:[/red bold] {message}")
    if details:
        for d in details:
            title = d.get("title", "")
            detail = d.get("detail", "")
            console.print(f"  [dim]{title}:[/dim] {detail}")
    console.print()
