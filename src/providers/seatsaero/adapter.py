"""Seats.aero award flight provider.

Searches award/redemption availability across 20+ mileage programs.
API docs: https://developers.seats.aero/reference/getting-started-p
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from ..base import ProviderError


@dataclass
class CabinAward:
    """Award availability for a single cabin class."""
    available: bool
    mileage_cost: int
    airlines: list[str]
    direct: bool
    remaining_seats: int = 0


@dataclass
class AwardResult:
    """Award availability for a route on a specific date."""
    id: str
    origin: str
    destination: str
    date: str
    source: str  # mileage program (aeroplan, united, etc.)
    cabins: dict[str, CabinAward]  # Y, W, J, F
    updated_at: Optional[str] = None
    
    @property
    def has_economy(self) -> bool:
        return self.cabins.get("Y", CabinAward(False, 0, [], False)).available
    
    @property
    def has_business(self) -> bool:
        return self.cabins.get("J", CabinAward(False, 0, [], False)).available
    
    @property
    def has_first(self) -> bool:
        return self.cabins.get("F", CabinAward(False, 0, [], False)).available
    
    @property
    def best_cabin(self) -> Optional[str]:
        """Return best available cabin."""
        for cabin in ["F", "J", "W", "Y"]:
            if self.cabins.get(cabin, CabinAward(False, 0, [], False)).available:
                return cabin
        return None


@dataclass
class AwardSearchResponse:
    """Response from award search."""
    results: list[AwardResult]
    count: int
    has_more: bool
    cursor: Optional[int] = None


# Mileage program display names
PROGRAM_NAMES = {
    "aeroplan": "Aeroplan",
    "united": "United MileagePlus",
    "american": "AAdvantage",
    "alaska": "Alaska Mileage Plan",
    "delta": "Delta SkyMiles",
    "virginatlantic": "Virgin Atlantic",
    "aerlingus": "Aer Lingus Avios",
    "qantas": "Qantas",
    "velocity": "Velocity",
    "emirates": "Emirates Skywards",
    "etihad": "Etihad Guest",
    "singapore": "KrisFlyer",
    "lifemiles": "LifeMiles",
    "smiles": "Smiles",
    "eurobonus": "SAS EuroBonus",
    "flyingblue": "Flying Blue",
    "connectmiles": "ConnectMiles",
}

CABIN_NAMES = {
    "Y": "Economy",
    "W": "Premium Economy",
    "J": "Business",
    "F": "First",
}


class SeatsAeroProvider:
    """Seats.aero award flight provider.
    
    Searches award availability across multiple mileage programs.
    Requires a Pro subscription for API access.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        load_dotenv()
        
        self.api_key = api_key or os.getenv("SEATSAERO_API_KEY")
        self.base_url = (base_url or "https://seats.aero/partnerapi").rstrip("/")
        
        if not self.api_key:
            raise ProviderError("SEATSAERO_API_KEY required")
        
        self._http = httpx.Client(timeout=30.0)
    
    @property
    def name(self) -> str:
        return "seatsaero"
    
    def _request(self, method: str, endpoint: str, params: Optional[dict] = None, json: Optional[dict] = None) -> dict:
        """Make a request to Seats.aero API."""
        headers = {
            "Partner-Authorization": self.api_key,
            "Accept": "application/json",
        }
        
        url = f"{self.base_url}{endpoint}"
        
        if method == "GET":
            response = self._http.get(url, params=params, headers=headers)
        else:
            headers["Content-Type"] = "application/json"
            response = self._http.post(url, params=params, json=json, headers=headers)
        
        if response.status_code == 401:
            raise ProviderError("Invalid API key", status_code=401)
        elif response.status_code == 429:
            raise ProviderError("Rate limit exceeded (1000 calls/day for Pro)", status_code=429)
        elif response.status_code != 200:
            raise ProviderError(
                f"Seats.aero request failed: {response.status_code}",
                status_code=response.status_code,
            )
        
        return response.json()
    
    def _parse_result(self, item: dict) -> AwardResult:
        """Parse a single availability result."""
        route = item.get("Route", {})
        
        def parse_cabin(prefix: str) -> CabinAward:
            available = item.get(f"{prefix}Available", False)
            cost_str = item.get(f"{prefix}MileageCost", "0")
            cost = int(cost_str) if cost_str and cost_str != "0" else 0
            airlines_str = item.get(f"{prefix}Airlines", "")
            airlines = [a.strip() for a in airlines_str.split(",") if a.strip()]
            direct = item.get(f"{prefix}Direct", False)
            seats = item.get(f"{prefix}RemainingSeats", 0)
            
            return CabinAward(
                available=available,
                mileage_cost=cost,
                airlines=airlines,
                direct=direct,
                remaining_seats=seats,
            )
        
        return AwardResult(
            id=item.get("ID", ""),
            origin=route.get("OriginAirport", item.get("OriginAirport", "")),
            destination=route.get("DestinationAirport", item.get("DestinationAirport", "")),
            date=item.get("Date", ""),
            source=item.get("Source", route.get("Source", "")),
            cabins={
                "Y": parse_cabin("Y"),
                "W": parse_cabin("W"),
                "J": parse_cabin("J"),
                "F": parse_cabin("F"),
            },
            updated_at=item.get("UpdatedAt"),
        )
    
    def search_awards(
        self,
        origin: str,
        destination: str,
        start_date: str,
        end_date: Optional[str] = None,
        cabins: Optional[list[str]] = None,
        sources: Optional[list[str]] = None,
        carriers: Optional[list[str]] = None,
        direct_only: bool = False,
        order_by: Optional[str] = None,  # "lowest_mileage" or None
        take: int = 100,
    ) -> AwardSearchResponse:
        """Search for award availability.
        
        Args:
            origin: Origin airport(s), comma-separated IATA codes
            destination: Destination airport(s), comma-separated IATA codes
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to start_date
            cabins: Filter by cabin classes (Y, W, J, F)
            sources: Filter by mileage programs (aeroplan, united, etc.)
            carriers: Filter by operating airlines (EK, AA, etc.)
            direct_only: Only show direct flights
            order_by: Sort order ("lowest_mileage" for cheapest first)
            take: Max results (10-1000)
        
        Returns:
            AwardSearchResponse with matching results
        """
        params = {
            "origin_airport": origin.upper(),
            "destination_airport": destination.upper(),
            "take": min(max(take, 10), 1000),
            "include_trips": "false",
        }
        
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        elif start_date:
            params["end_date"] = start_date  # Single day search
        
        if cabins:
            # Convert our codes to seats.aero format
            cabin_map = {"Y": "economy", "W": "premium", "J": "business", "F": "first"}
            params["cabins"] = ",".join(cabin_map.get(c.upper(), c.lower()) for c in cabins)
        
        if sources:
            params["sources"] = ",".join(s.lower() for s in sources)
        
        if carriers:
            params["carriers"] = ",".join(c.upper() for c in carriers)
        
        if direct_only:
            params["only_direct_flights"] = "true"
        
        if order_by:
            params["order_by"] = order_by
        
        data = self._request("GET", "/search", params=params)
        
        results = [self._parse_result(item) for item in data.get("data", [])]
        
        return AwardSearchResponse(
            results=results,
            count=len(results),
            has_more=data.get("hasMore", False),
            cursor=data.get("cursor"),
        )
    
    def get_routes(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        source: Optional[str] = None,
    ) -> list[dict]:
        """Get available routes.
        
        Args:
            origin: Filter by origin airport
            destination: Filter by destination airport
            source: Filter by mileage program
        
        Returns:
            List of route objects
        """
        params = {}
        if origin:
            params["origin_airport"] = origin.upper()
        if destination:
            params["destination_airport"] = destination.upper()
        if source:
            params["source"] = source.lower()
        
        data = self._request("GET", "/routes", params=params)
        return data.get("data", [])
    
    def close(self) -> None:
        """Close HTTP client."""
        self._http.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


def format_mileage(miles: int) -> str:
    """Format mileage with thousands separator."""
    if miles >= 1000:
        return f"{miles:,}"
    return str(miles)


def format_program_name(source: str) -> str:
    """Get display name for mileage program."""
    return PROGRAM_NAMES.get(source.lower(), source.title())
