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
    Itinerary,
)

console = Console()


# Common IATA aircraft codes → full names
AIRCRAFT_CODES = {
    # Airbus
    "318": "Airbus A318",
    "319": "Airbus A319",
    "320": "Airbus A320",
    "32A": "Airbus A320 (Sharklets)",
    "32N": "Airbus A320neo",
    "321": "Airbus A321",
    "32Q": "Airbus A321neo",
    "332": "Airbus A330-200",
    "333": "Airbus A330-300",
    "338": "Airbus A330-800neo",
    "339": "Airbus A330-900neo",
    "342": "Airbus A340-200",
    "343": "Airbus A340-300",
    "345": "Airbus A340-500",
    "346": "Airbus A340-600",
    "350": "Airbus A350",
    "351": "Airbus A350-1000",
    "359": "Airbus A350-900",
    "380": "Airbus A380",
    "388": "Airbus A380-800",
    # Boeing
    "737": "Boeing 737",
    "738": "Boeing 737-800",
    "739": "Boeing 737-900",
    "7M8": "Boeing 737 MAX 8",
    "7M9": "Boeing 737 MAX 9",
    "744": "Boeing 747-400",
    "748": "Boeing 747-8",
    "752": "Boeing 757-200",
    "753": "Boeing 757-300",
    "762": "Boeing 767-200",
    "763": "Boeing 767-300",
    "764": "Boeing 767-400",
    "772": "Boeing 777-200",
    "773": "Boeing 777-300",
    "77W": "Boeing 777-300ER",
    "77L": "Boeing 777-200LR",
    "779": "Boeing 777-9",
    "787": "Boeing 787",
    "788": "Boeing 787-8",
    "789": "Boeing 787-9",
    "78X": "Boeing 787-10",
    # Embraer
    "E70": "Embraer E170",
    "E75": "Embraer E175",
    "E90": "Embraer E190",
    "E95": "Embraer E195",
    "E2E": "Embraer E195-E2",
    # Other
    "AT7": "ATR 72",
    "DH4": "Dash 8-400",
    "CR9": "CRJ-900",
    "CRJ": "CRJ",
}


def get_aircraft_name(code: Optional[str]) -> Optional[str]:
    """Get full aircraft name from IATA code."""
    if not code:
        return None
    # Check lookup table, fallback to code itself if already a full name
    return AIRCRAFT_CODES.get(code.upper(), code)


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
    return_date: Optional[str] = None,
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
                "return_date": return_date,
                "cabin": cabin,
                "adults": adults,
            },
            "results": [_offer_to_dict(o) for o in offers],
        }, indent=2))
        return
    
    # Parse date for nice formatting
    from datetime import datetime as dt
    try:
        dep_dt = dt.strptime(date, "%Y-%m-%d")
        date_nice = dep_dt.strftime("%a %d %b %Y")
    except:
        date_nice = date
    
    # Header
    adults_str = f"{adults} adult{'s' if adults > 1 else ''}"
    
    if return_date:
        try:
            ret_dt = dt.strptime(return_date, "%Y-%m-%d")
            return_nice = ret_dt.strftime("%a %d %b")
        except:
            return_nice = return_date
        console.print(f"\n✈  [bold]{origin} ↔ {destination}[/bold]  •  {date_nice} → {return_nice}  •  {adults_str}\n")
    else:
        console.print(f"\n✈  [bold]{origin} → {destination}[/bold]  •  {date_nice}  •  {adults_str}\n")
    
    if not offers:
        console.print("[yellow]No flights found[/yellow]")
        return
    
    if return_date:
        # Round-trip: show all results together
        _print_round_trip_offers(offers)
    else:
        # One-way: group by direct vs connecting
        direct = [o for o in offers if o.outbound.is_direct]
        connecting = [o for o in offers if not o.outbound.is_direct]
        
        if direct:
            console.print(f"[bold]DIRECT FLIGHTS[/bold] {'─' * 36}")
            for offer in direct:
                _print_oneway_offer(offer)
            console.print()
        
        if connecting:
            console.print(f"[bold]CONNECTING[/bold] {'─' * 39}")
            for offer in connecting:
                _print_oneway_offer(offer)
    
    console.print(f"\n[dim]{'─' * 50}[/dim]")
    console.print(f"[dim]Showing {len(offers)} results  •  Prices include taxes[/dim]\n")


def _print_oneway_offer(offer: FlightOffer):
    """Print a one-way flight offer in clean tabular format."""
    itin = offer.outbound
    
    # Get carrier and flight number
    carrier_name = itin.segments[0].carrier_name or itin.segments[0].carrier
    flight_code = itin.segments[0].flight_code
    
    # Shorten carrier name if needed
    short_carrier = carrier_name.split()[0] if carrier_name else ""
    
    # Times
    dep_time = format_time(itin.departure_time)
    arr_time = format_time(itin.arrival_time)
    day_change = day_diff(itin.departure_time, itin.arrival_time)
    if day_change:
        arr_time = f"{arr_time}{day_change}"
    
    # Price
    price_str = f"${offer.price.amount:,.0f}"
    
    # Right side: aircraft for direct, stops for connecting
    if itin.is_direct:
        aircraft = itin.segments[0].aircraft
        right_info = f"• {get_aircraft_name(aircraft)}" if aircraft else ""
    else:
        stop_codes = [seg.arrival.code for seg in itin.segments[:-1]]
        stops_word = "stop" if itin.stops == 1 else "stops"
        right_info = f"• {itin.stops} {stops_word} {','.join(stop_codes)}"
    
    # Format: "Airline FL123    09:40 → 14:40    $433   • Aircraft"
    console.print(f"  {short_carrier} {flight_code:<8} {dep_time} → {arr_time:<8} {price_str:>8}   {right_info}")


def _print_round_trip_offers(offers: list[FlightOffer]):
    """Print round-trip offers with both legs."""
    # Group by direct vs connecting (based on outbound)
    direct = [o for o in offers if o.outbound.is_direct and (len(o.itineraries) < 2 or o.itineraries[1].is_direct)]
    mixed = [o for o in offers if o not in direct]
    
    if direct:
        console.print(f"[bold]DIRECT[/bold] {'─' * 44}")
        for offer in direct:
            _print_rt_offer(offer)
        console.print()
    
    if mixed:
        console.print(f"[bold]CONNECTING[/bold] {'─' * 39}")
        for offer in mixed:
            _print_rt_offer(offer)


def _print_rt_offer(offer: FlightOffer):
    """Print a single round-trip offer."""
    out = offer.outbound
    ret = offer.itineraries[1] if len(offer.itineraries) > 1 else None
    
    # Carrier
    carrier_name = out.segments[0].carrier_name or out.segments[0].carrier
    short_carrier = carrier_name.split()[0] if carrier_name else ""
    
    # Price
    price_str = f"${offer.price.amount:,.0f}"
    
    # Outbound info
    out_flights = "+".join(seg.flight_code for seg in out.segments)
    out_times = f"{format_time(out.departure_time)}→{format_time(out.arrival_time)}"
    out_day = day_diff(out.departure_time, out.arrival_time)
    if out_day:
        out_times = f"{format_time(out.departure_time)}→{format_time(out.arrival_time)}{out_day}"
    
    if ret:
        # Return info
        ret_flights = "+".join(seg.flight_code for seg in ret.segments)
        ret_times = f"{format_time(ret.departure_time)}→{format_time(ret.arrival_time)}"
        ret_day = day_diff(ret.departure_time, ret.arrival_time)
        if ret_day:
            ret_times = f"{format_time(ret.departure_time)}→{format_time(ret.arrival_time)}{ret_day}"
        
        # Stops info
        out_stops = "" if out.is_direct else f" ({out.stops}x)"
        ret_stops = "" if ret.is_direct else f" ({ret.stops}x)"
        
        console.print(f"  [bold]{short_carrier}[/bold]  {out_times}{out_stops}  ⇄  {ret_times}{ret_stops}  [green bold]{price_str}[/green bold]")
        console.print(f"    [dim]OUT {out_flights}  •  RET {ret_flights}[/dim]")
    else:
        console.print(f"  [bold]{short_carrier}[/bold]  {out_times}  [green bold]{price_str}[/green bold]  [dim]{out_flights}[/dim]")


def _print_offer_legacy(offer: FlightOffer, is_round_trip: bool = False):
    """Legacy print function (kept for reference)."""
    pass


def _offer_to_dict(offer: FlightOffer) -> dict:
    """Convert offer to JSON-serializable dict."""
    def itinerary_to_dict(itin: Itinerary) -> dict:
        return {
            "duration": itin.duration,
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
                    "aircraft": seg.aircraft,
                }
                for seg in itin.segments
            ],
        }
    
    result = {
        "price": {"amount": offer.price.amount, "currency": offer.price.currency},
    }
    
    if len(offer.itineraries) == 1:
        result["itinerary"] = itinerary_to_dict(offer.outbound)
    else:
        result["itineraries"] = [itinerary_to_dict(itin) for itin in offer.itineraries]
    
    return result


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
    
    # Details line 1: Duration
    if duration:
        console.print(f"  [dim]Duration: {duration}[/dim]")
    
    # Details line 2: Aircraft
    if sched.aircraft:
        aircraft_name = get_aircraft_name(sched.aircraft)
        console.print(f"  [cyan]Aircraft: {aircraft_name}[/cyan]")
    
    # Status if available
    if sched.status:
        console.print(f"  [dim]Status: {sched.status}[/dim]")
    
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
