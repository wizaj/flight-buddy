"""SerpApi Google Flights provider implementation.

Scrapes Google Flights via SerpApi. Read-only (no booking).
API docs: https://serpapi.com/google-flights-api
"""

import os
from datetime import datetime
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from ..base import FlightProvider, ProviderError
from ...models import (
    FlightOffer, FlightSchedule, FlightAvailability, SeatMap,
    Itinerary, Segment, Airport, Price
)


# Cabin class mapping: our codes -> SerpApi codes
CABIN_MAP = {
    "economy": 1, "Y": 1,
    "premium": 2, "W": 2, "premium_economy": 2,
    "business": 3, "J": 3,
    "first": 4, "F": 4,
}

# Reverse mapping: SerpApi travel_class -> our cabin codes  
CABIN_REVERSE = {
    "Economy": "ECONOMY",
    "Premium economy": "PREMIUM_ECONOMY",
    "Business": "BUSINESS",
    "First": "FIRST",
}


class SerpApiProvider(FlightProvider):
    """SerpApi Google Flights provider.
    
    Scrapes Google Flights and returns structured data.
    Good for: search, prices, flight info
    Not supported: seat maps, availability by class, direct booking
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        load_dotenv()
        
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self.base_url = (base_url or "https://serpapi.com").rstrip("/")
        
        if not self.api_key:
            raise ProviderError("SERPAPI_API_KEY required")
        
        self._http = httpx.Client(timeout=60.0)  # SerpApi can be slow
    
    @property
    def name(self) -> str:
        return "serpapi"
    
    def _request(self, params: dict) -> dict:
        """Make a request to SerpApi."""
        params = {
            "engine": "google_flights",
            "api_key": self.api_key,
            "hl": "en",
            **params,
        }
        
        response = self._http.get(f"{self.base_url}/search", params=params)
        
        if response.status_code != 200:
            raise ProviderError(
                f"SerpApi request failed: {response.status_code}",
                status_code=response.status_code,
            )
        
        data = response.json()
        
        # Check for API errors
        if "error" in data:
            raise ProviderError(f"SerpApi error: {data['error']}")
        
        return data
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        cabin: Optional[str] = None,
        non_stop: bool = False,
        airlines: Optional[list[str]] = None,
        exclude_airlines: Optional[list[str]] = None,
        max_results: int = 10,
        currency: str = "USD",
    ) -> list[FlightOffer]:
        """Search for flights via Google Flights."""
        
        # Type 1 = round-trip, Type 2 = one-way
        flight_type = 1 if return_date else 2
        
        params = {
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": departure_date,
            "type": flight_type,
            "adults": adults,
            "currency": currency,
        }
        
        # Add return date for round-trip
        if return_date:
            params["return_date"] = return_date
        
        # Map cabin class and store for later
        requested_cabin = "ECONOMY"  # Default
        if cabin:
            cabin_code = CABIN_MAP.get(cabin.lower(), CABIN_MAP.get(cabin))
            if cabin_code:
                params["travel_class"] = cabin_code
                # Map code to cabin name
                requested_cabin = {1: "ECONOMY", 2: "PREMIUM_ECONOMY", 3: "BUSINESS", 4: "FIRST"}.get(cabin_code, "ECONOMY")
        
        # Non-stop filter
        if non_stop:
            params["stops"] = 1  # 1 = nonstop only
        
        # Airline filters
        if airlines:
            params["include_airlines"] = ",".join(airlines)
        if exclude_airlines:
            params["exclude_airlines"] = ",".join(exclude_airlines)
        
        data = self._request(params)
        
        # Combine best_flights and other_flights
        all_flights = data.get("best_flights", []) + data.get("other_flights", [])
        
        offers = []
        
        if return_date:
            # Round-trip: need to fetch return options for each outbound
            # Limit to top N to avoid excessive API calls
            max_outbound = min(max_results, 5)  # Cap outbound options
            
            for i, outbound_data in enumerate(all_flights[:max_outbound]):
                try:
                    departure_token = outbound_data.get("departure_token")
                    if not departure_token:
                        continue
                    
                    # Fetch return options for this outbound
                    return_params = {
                        **params,
                        "departure_token": departure_token,
                    }
                    return_data = self._request(return_params)
                    
                    # Get return flights (usually in other_flights when using departure_token)
                    return_flights = return_data.get("best_flights", []) + return_data.get("other_flights", [])
                    
                    if return_flights:
                        # Take best return option for this outbound
                        best_return = return_flights[0]
                        offer = self._parse_round_trip_offer(
                            outbound_data, best_return, currency, i, requested_cabin
                        )
                        offers.append(offer)
                except Exception as e:
                    # Skip malformed results
                    continue
        else:
            # One-way: original logic
            for i, flight_data in enumerate(all_flights[:max_results]):
                try:
                    offer = self._parse_flight_offer(flight_data, currency, i, requested_cabin, is_round_trip=False)
                    offers.append(offer)
                except Exception as e:
                    continue
        
        return offers
    
    def _parse_flight_offer(self, data: dict, currency: str, index: int, requested_cabin: str = "ECONOMY", is_round_trip: bool = False) -> FlightOffer:
        """Parse a SerpApi flight result into FlightOffer."""
        
        itineraries = []
        
        # For round-trip, SerpApi nests flights in a list of legs
        # Each leg is an outbound or return journey
        if is_round_trip and isinstance(data.get("flights"), list) and len(data.get("flights", [])) > 0:
            # Check if we have nested structure (round-trip) or flat structure (one-way)
            first_item = data["flights"][0]
            if isinstance(first_item, list):
                # Round-trip: flights is a list of legs, each leg is a list of segments
                for leg_flights in data["flights"]:
                    segments = []
                    for flight in leg_flights:
                        segment = self._parse_segment(flight, requested_cabin)
                        segments.append(segment)
                    if segments:
                        # Calculate duration for this leg
                        leg_duration = self._calculate_leg_duration(leg_flights)
                        itineraries.append(Itinerary(segments=segments, duration=leg_duration))
            else:
                # Flat structure (one-way style even in round-trip response)
                segments = []
                for flight in data.get("flights", []):
                    segment = self._parse_segment(flight, requested_cabin)
                    segments.append(segment)
                total_mins = data.get("total_duration", 0)
                hours, mins = divmod(total_mins, 60)
                duration_str = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
                itineraries.append(Itinerary(segments=segments, duration=duration_str))
        else:
            # One-way: original logic
            segments = []
            for flight in data.get("flights", []):
                segment = self._parse_segment(flight, requested_cabin)
                segments.append(segment)
            
            total_mins = data.get("total_duration", 0)
            hours, mins = divmod(total_mins, 60)
            duration_str = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
            
            itineraries.append(Itinerary(segments=segments, duration=duration_str))
        
        # Build ID from booking token or index
        booking_token = data.get("booking_token", "")
        offer_id = booking_token[:20] if booking_token else f"serp-{index}"
        
        # Get validating carrier from first segment of first itinerary
        validating = itineraries[0].segments[0].carrier if itineraries and itineraries[0].segments else None
        
        return FlightOffer(
            id=offer_id,
            source="serpapi",
            price=Price(
                amount=float(data.get("price", 0)),
                currency=currency,
            ),
            itineraries=itineraries,
            validating_carrier=validating,
            raw=data,  # Keep original for debugging
        )
    
    def _parse_round_trip_offer(
        self, 
        outbound_data: dict, 
        return_data: dict, 
        currency: str, 
        index: int, 
        requested_cabin: str = "ECONOMY"
    ) -> FlightOffer:
        """Parse outbound + return data into a single round-trip FlightOffer."""
        
        # Parse outbound itinerary
        outbound_segments = []
        for flight in outbound_data.get("flights", []):
            segment = self._parse_segment(flight, requested_cabin)
            outbound_segments.append(segment)
        
        outbound_mins = outbound_data.get("total_duration", 0)
        hours, mins = divmod(outbound_mins, 60)
        outbound_duration = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
        
        outbound_itin = Itinerary(segments=outbound_segments, duration=outbound_duration)
        
        # Parse return itinerary
        return_segments = []
        for flight in return_data.get("flights", []):
            segment = self._parse_segment(flight, requested_cabin)
            return_segments.append(segment)
        
        return_mins = return_data.get("total_duration", 0)
        hours, mins = divmod(return_mins, 60)
        return_duration = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
        
        return_itin = Itinerary(segments=return_segments, duration=return_duration)
        
        # Use price from return_data as it's the final round-trip price
        price = return_data.get("price", outbound_data.get("price", 0))
        
        # Build ID from booking token
        booking_token = return_data.get("booking_token", "")
        offer_id = booking_token[:20] if booking_token else f"serp-rt-{index}"
        
        # Get validating carrier from first segment
        validating = outbound_segments[0].carrier if outbound_segments else None
        
        return FlightOffer(
            id=offer_id,
            source="serpapi",
            price=Price(amount=float(price), currency=currency),
            itineraries=[outbound_itin, return_itin],
            validating_carrier=validating,
            raw={"outbound": outbound_data, "return": return_data},
        )
    
    def _calculate_leg_duration(self, leg_flights: list) -> str:
        """Calculate total duration for a leg from its flights."""
        total_mins = sum(f.get("duration", 0) for f in leg_flights)
        # Add layover time if multiple flights
        if len(leg_flights) > 1:
            for i in range(len(leg_flights) - 1):
                arr_time = leg_flights[i].get("arrival_airport", {}).get("time", "")
                dep_time = leg_flights[i + 1].get("departure_airport", {}).get("time", "")
                if arr_time and dep_time:
                    arr_dt = self._parse_datetime(arr_time)
                    dep_dt = self._parse_datetime(dep_time)
                    if arr_dt and dep_dt:
                        layover = (dep_dt - arr_dt).total_seconds() / 60
                        total_mins += int(layover)
        hours, mins = divmod(int(total_mins), 60)
        return f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
    
    def _parse_segment(self, flight: dict, requested_cabin: str = "ECONOMY") -> Segment:
        """Parse a flight segment from SerpApi data."""
        
        dep = flight.get("departure_airport", {})
        arr = flight.get("arrival_airport", {})
        
        # Parse flight number (e.g., "EK 766" -> "EK", "766")
        flight_num_parts = flight.get("flight_number", "XX 0").split()
        carrier = flight_num_parts[0] if flight_num_parts else "XX"
        number = flight_num_parts[1] if len(flight_num_parts) > 1 else "0"
        
        # Parse times
        dep_time = self._parse_datetime(dep.get("time", ""))
        arr_time = self._parse_datetime(arr.get("time", ""))
        
        # Duration in ISO 8601
        duration_mins = flight.get("duration", 0)
        hours, mins = divmod(duration_mins, 60)
        duration_str = f"PT{hours}H{mins}M" if hours else f"PT{mins}M"
        
        # Use requested cabin (SerpApi often returns wrong cabin label)
        # Fall back to their label if they provide one that looks right
        api_cabin = CABIN_REVERSE.get(flight.get("travel_class", ""), None)
        cabin = api_cabin if api_cabin and api_cabin != "ECONOMY" else requested_cabin
        
        return Segment(
            carrier=carrier,
            carrier_name=flight.get("airline", ""),
            flight_number=number,
            departure=Airport(
                code=dep.get("id", ""),
                name=dep.get("name", ""),
            ),
            departure_time=dep_time or datetime.now(),
            arrival=Airport(
                code=arr.get("id", ""),
                name=arr.get("name", ""),
            ),
            arrival_time=arr_time or datetime.now(),
            duration=duration_str,
            aircraft=flight.get("airplane"),
            cabin=cabin,
        )
    
    def _parse_datetime(self, time_str: str) -> Optional[datetime]:
        """Parse SerpApi datetime string (e.g., '2026-02-01 10:30')."""
        if not time_str:
            return None
        try:
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    
    def get_flight_schedule(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
    ) -> list[FlightSchedule]:
        """Not supported by SerpApi - no direct flight lookup."""
        raise NotImplementedError(
            "SerpApi doesn't support flight schedule lookup. "
            "Use 'search' to find flights by route instead."
        )
    
    def get_flight_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        departure_time: Optional[str] = None,
        carrier_code: Optional[str] = None,
        flight_number: Optional[str] = None,
    ) -> list[FlightAvailability]:
        """Not supported by SerpApi - no cabin availability data."""
        raise NotImplementedError(
            "SerpApi doesn't expose seat availability by cabin class."
        )
    
    def get_seat_map(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
        origin: str,
        destination: str,
    ) -> Optional[SeatMap]:
        """Not supported - Google Flights doesn't show seat maps."""
        return None
    
    def get_price_insights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        currency: str = "USD",
    ) -> Optional[dict]:
        """Get price insights from Google Flights.
        
        Returns:
            {
                "lowest_price": 520,
                "price_level": "low",  # "low", "typical", "high"
                "typical_price_range": [690, 1350],
                "price_history": [[timestamp, price], ...]
            }
        """
        params = {
            "departure_id": origin.upper(),
            "arrival_id": destination.upper(),
            "outbound_date": departure_date,
            "type": 2,
            "currency": currency,
        }
        
        data = self._request(params)
        return data.get("price_insights")
    
    def close(self) -> None:
        """Close HTTP client."""
        self._http.close()
