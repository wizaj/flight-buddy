"""Data models for Amadeus API responses."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Airport:
    """Airport information."""
    code: str
    name: Optional[str] = None
    terminal: Optional[str] = None


@dataclass
class Segment:
    """A single flight segment."""
    carrier: str
    carrier_name: Optional[str]
    flight_number: str
    aircraft: Optional[str]
    departure: Airport
    departure_time: datetime
    arrival: Airport
    arrival_time: datetime
    duration: str  # ISO 8601 duration (PT8H30M)
    cabin: Optional[str] = None
    booking_class: Optional[str] = None
    
    @property
    def flight_code(self) -> str:
        """Full flight code (e.g., EK766)."""
        return f"{self.carrier}{self.flight_number}"
    
    @property
    def duration_human(self) -> str:
        """Human readable duration (e.g., 8h30m)."""
        d = self.duration.replace("PT", "").lower()
        return d


@dataclass
class Itinerary:
    """A complete itinerary (may have multiple segments)."""
    segments: list[Segment]
    duration: str  # Total duration
    
    @property
    def is_direct(self) -> bool:
        return len(self.segments) == 1
    
    @property
    def stops(self) -> int:
        return len(self.segments) - 1
    
    @property
    def origin(self) -> Airport:
        return self.segments[0].departure
    
    @property
    def destination(self) -> Airport:
        return self.segments[-1].arrival
    
    @property
    def departure_time(self) -> datetime:
        return self.segments[0].departure_time
    
    @property
    def arrival_time(self) -> datetime:
        return self.segments[-1].arrival_time


@dataclass
class Price:
    """Price information."""
    amount: float
    currency: str
    
    def __str__(self) -> str:
        if self.currency == "ZAR":
            return f"R {self.amount:,.0f}"
        elif self.currency == "USD":
            return f"${self.amount:,.2f}"
        elif self.currency == "EUR":
            return f"€{self.amount:,.2f}"
        else:
            return f"{self.currency} {self.amount:,.2f}"


@dataclass
class FlightOffer:
    """A complete flight offer with pricing."""
    id: str
    source: str
    price: Price
    itineraries: list[Itinerary]
    validating_carrier: Optional[str] = None
    raw: dict = field(default_factory=dict, repr=False)
    
    @property
    def outbound(self) -> Itinerary:
        return self.itineraries[0]
    
    @property
    def cabin(self) -> Optional[str]:
        """Primary cabin class."""
        if self.itineraries and self.itineraries[0].segments:
            return self.itineraries[0].segments[0].cabin
        return None


@dataclass
class FlightSchedule:
    """Flight schedule information."""
    carrier: str
    carrier_name: Optional[str]
    flight_number: str
    departure: Airport
    departure_time: datetime
    arrival: Airport
    arrival_time: datetime
    duration: str
    aircraft: Optional[str] = None
    status: Optional[str] = None
    
    @property
    def flight_code(self) -> str:
        return f"{self.carrier}{self.flight_number}"


@dataclass
class CabinAvailability:
    """Availability for a specific cabin class."""
    cabin: str  # ECONOMY, BUSINESS, etc.
    booking_class: str  # Y, J, F, etc.
    available: int  # Number of seats


@dataclass
class FlightAvailability:
    """Availability information for a flight."""
    carrier: str
    flight_number: str
    departure: Airport
    departure_time: datetime
    arrival: Airport
    arrival_time: datetime
    cabins: list[CabinAvailability]
    
    @property
    def flight_code(self) -> str:
        return f"{self.carrier}{self.flight_number}"
    
    def get_cabin(self, cabin: str) -> Optional[CabinAvailability]:
        """Get availability for specific cabin."""
        cabin = cabin.upper()
        for c in self.cabins:
            if c.cabin == cabin or c.booking_class == cabin:
                return c
        return None


@dataclass
class Seat:
    """Individual seat information."""
    number: str  # e.g., "1A"
    available: bool
    cabin: str
    characteristics: list[str] = field(default_factory=list)  # WINDOW, AISLE, etc.
    
    @property
    def row(self) -> int:
        return int("".join(c for c in self.number if c.isdigit()))
    
    @property
    def column(self) -> str:
        return "".join(c for c in self.number if c.isalpha())


@dataclass
class SeatMap:
    """Seat map for a flight."""
    carrier: str
    flight_number: str
    aircraft: Optional[str]
    departure: Airport
    arrival: Airport
    departure_date: str
    decks: list[list[Seat]]  # List of decks, each with seats
    
    @property
    def flight_code(self) -> str:
        return f"{self.carrier}{self.flight_number}"
    
    def seats_by_cabin(self, cabin: str) -> list[Seat]:
        """Get all seats for a cabin class."""
        cabin = cabin.upper()
        result = []
        for deck in self.decks:
            for seat in deck:
                if seat.cabin == cabin:
                    result.append(seat)
        return result
    
    def available_count(self, cabin: Optional[str] = None) -> int:
        """Count available seats, optionally filtered by cabin."""
        count = 0
        for deck in self.decks:
            for seat in deck:
                if seat.available:
                    if cabin is None or seat.cabin == cabin.upper():
                        count += 1
        return count


# ─────────────────────────────────────────────────────────────
# Response Parsers
# ─────────────────────────────────────────────────────────────

def parse_datetime(date_str: str) -> datetime:
    """Parse ISO datetime string."""
    # Strip timezone suffix if present
    date_str = date_str.rstrip("Z")
    if "+" in date_str:
        date_str = date_str.split("+")[0]
    
    # Handle various formats
    for fmt in ["%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"]:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {date_str}")


def parse_flight_offers(response: dict) -> list[FlightOffer]:
    """Parse flight offers search response."""
    data = response.get("data", [])
    dictionaries = response.get("dictionaries", {})
    carriers = dictionaries.get("carriers", {})
    aircraft = dictionaries.get("aircraft", {})
    
    offers = []
    for item in data:
        itineraries = []
        for itin in item.get("itineraries", []):
            segments = []
            for seg in itin.get("segments", []):
                carrier_code = seg.get("carrierCode", "")
                segments.append(Segment(
                    carrier=carrier_code,
                    carrier_name=carriers.get(carrier_code),
                    flight_number=seg.get("number", ""),
                    aircraft=aircraft.get(seg.get("aircraft", {}).get("code")),
                    departure=Airport(
                        code=seg.get("departure", {}).get("iataCode", ""),
                        terminal=seg.get("departure", {}).get("terminal"),
                    ),
                    departure_time=parse_datetime(seg.get("departure", {}).get("at", "")),
                    arrival=Airport(
                        code=seg.get("arrival", {}).get("iataCode", ""),
                        terminal=seg.get("arrival", {}).get("terminal"),
                    ),
                    arrival_time=parse_datetime(seg.get("arrival", {}).get("at", "")),
                    duration=seg.get("duration", ""),
                ))
            itineraries.append(Itinerary(
                segments=segments,
                duration=itin.get("duration", ""),
            ))
        
        price_data = item.get("price", {})
        offers.append(FlightOffer(
            id=item.get("id", ""),
            source=item.get("source", ""),
            price=Price(
                amount=float(price_data.get("grandTotal", price_data.get("total", 0))),
                currency=price_data.get("currency", "USD"),
            ),
            itineraries=itineraries,
            validating_carrier=item.get("validatingAirlineCodes", [None])[0],
            raw=item,
        ))
    
    return offers


def parse_flight_schedule(response: dict) -> list[FlightSchedule]:
    """Parse flight schedule response."""
    data = response.get("data", [])
    
    schedules = []
    for item in data:
        flight_points = item.get("flightPoints", [])
        if len(flight_points) < 2:
            continue
        
        dep = flight_points[0]
        arr = flight_points[-1]
        
        segments = item.get("segments", [{}])
        segment = segments[0] if segments else {}
        legs = item.get("legs", [{}])
        leg = legs[0] if legs else {}
        
        dep_time_data = dep.get("departure", {})
        arr_time_data = arr.get("arrival", {})
        
        # Aircraft is in legs[].aircraftEquipment.aircraftType
        aircraft = leg.get("aircraftEquipment", {}).get("aircraftType")
        
        schedules.append(FlightSchedule(
            carrier=item.get("flightDesignator", {}).get("carrierCode", ""),
            carrier_name=None,  # Not in schedule response
            flight_number=str(item.get("flightDesignator", {}).get("flightNumber", "")),
            departure=Airport(
                code=dep.get("iataCode", ""),
                terminal=dep_time_data.get("terminal", {}).get("code"),
            ),
            departure_time=parse_datetime(dep_time_data.get("timings", [{}])[0].get("value", "")),
            arrival=Airport(
                code=arr.get("iataCode", ""),
                terminal=arr_time_data.get("terminal", {}).get("code"),
            ),
            arrival_time=parse_datetime(arr_time_data.get("timings", [{}])[0].get("value", "")),
            duration=segment.get("scheduledSegmentDuration", ""),
            aircraft=aircraft,
            status=item.get("status"),
        ))
    
    return schedules


def parse_seat_map(response: dict) -> Optional[SeatMap]:
    """Parse seat map response."""
    data = response.get("data", [])
    if not data:
        return None
    
    item = data[0]
    decks_data = item.get("decks", [])
    
    decks = []
    for deck_data in decks_data:
        seats_data = deck_data.get("seats", [])
        deck_seats = []
        
        for seat_data in seats_data:
            # Get availability status
            traveler_pricing = seat_data.get("travelerPricing", [{}])
            status = "AVAILABLE"
            if traveler_pricing:
                status = traveler_pricing[0].get("seatAvailabilityStatus", "AVAILABLE")
            
            available = status == "AVAILABLE"
            
            # Get characteristics
            chars = seat_data.get("characteristicsCodes", [])
            characteristics = []
            char_map = {
                "W": "WINDOW",
                "A": "AISLE",
                "1": "RESTRICTED_RECLINE",
                "E": "EXIT_ROW",
                "L": "LEG_SPACE",
                "CH": "CHARGEABLE",
            }
            for c in chars:
                if c in char_map:
                    characteristics.append(char_map[c])
            
            deck_seats.append(Seat(
                number=seat_data.get("number", ""),
                available=available,
                cabin=seat_data.get("cabin", "ECONOMY"),
                characteristics=characteristics,
            ))
        
        decks.append(deck_seats)
    
    dep = item.get("departure", {})
    arr = item.get("arrival", {})
    
    return SeatMap(
        carrier=item.get("carrierCode", ""),
        flight_number=item.get("number", ""),
        aircraft=item.get("aircraft", {}).get("code"),
        departure=Airport(code=dep.get("iataCode", "")),
        arrival=Airport(code=arr.get("iataCode", "")),
        departure_date=dep.get("at", "")[:10] if dep.get("at") else "",
        decks=decks,
    )


def parse_flight_availability(response: dict) -> list[FlightAvailability]:
    """Parse flight availability response."""
    data = response.get("data", [])
    
    availabilities = []
    for item in data:
        segments = item.get("segments", [])
        if not segments:
            continue
        
        seg = segments[0]
        
        cabins = []
        for avail in seg.get("availabilityClasses", []):
            cabins.append(CabinAvailability(
                cabin=avail.get("cabin", "ECONOMY"),
                booking_class=avail.get("class", "Y"),
                available=avail.get("numberOfBookableSeats", 0),
            ))
        
        dep = seg.get("departure", {})
        arr = seg.get("arrival", {})
        
        availabilities.append(FlightAvailability(
            carrier=seg.get("carrierCode", ""),
            flight_number=seg.get("number", ""),
            departure=Airport(code=dep.get("iataCode", "")),
            departure_time=parse_datetime(dep.get("at", "")),
            arrival=Airport(code=arr.get("iataCode", "")),
            arrival_time=parse_datetime(arr.get("at", "")),
            cabins=cabins,
        ))
    
    return availabilities
