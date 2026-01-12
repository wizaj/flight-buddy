"""Duffel API provider implementation.

TODO: Implement Duffel integration
- API docs: https://duffel.com/docs/api
- Uses Bearer token auth (simpler than Amadeus OAuth)
- African coverage: 19 airlines via Travelport GDS
"""

import os
from typing import Optional

import httpx
from dotenv import load_dotenv

from ..base import FlightProvider, ProviderError
from ...models import FlightOffer, FlightSchedule, FlightAvailability, SeatMap


class DuffelProvider(FlightProvider):
    """Duffel API provider.
    
    Status: NOT YET IMPLEMENTED
    
    Key differences from Amadeus:
    - REST API with Bearer token (no OAuth dance)
    - Offer Requests → Offers → Orders flow
    - African airlines via Travelport GDS only (no direct connect)
    - Pricing: £2.20/order + 1% of order value
    """
    
    def __init__(
        self,
        access_token: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        load_dotenv()
        
        self.access_token = access_token or os.getenv("DUFFEL_ACCESS_TOKEN")
        self.base_url = (base_url or "https://api.duffel.com").rstrip("/")
        
        if not self.access_token:
            raise ProviderError("DUFFEL_ACCESS_TOKEN required")
        
        self._http = httpx.Client(timeout=30.0)
    
    @property
    def name(self) -> str:
        return "duffel"
    
    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "application/json",
            "Duffel-Version": "v1",
        }
    
    def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        cabin: Optional[str] = None,
        non_stop: bool = False,
        airlines: Optional[list[str]] = None,
        exclude_airlines: Optional[list[str]] = None,
        max_results: int = 10,
        currency: str = "USD",
    ) -> list[FlightOffer]:
        # TODO: Implement using Duffel Offer Requests API
        # POST /air/offer_requests
        raise NotImplementedError("Duffel provider not yet implemented")
    
    def get_flight_schedule(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
    ) -> list[FlightSchedule]:
        # Duffel doesn't have a direct schedule lookup API
        # Would need to search and filter
        raise NotImplementedError("Duffel provider not yet implemented")
    
    def get_flight_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        departure_time: Optional[str] = None,
        carrier_code: Optional[str] = None,
        flight_number: Optional[str] = None,
    ) -> list[FlightAvailability]:
        # Duffel includes availability in offer responses
        raise NotImplementedError("Duffel provider not yet implemented")
    
    def get_seat_map(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
        origin: str,
        destination: str,
    ) -> Optional[SeatMap]:
        # Duffel seat maps only available for Direct Connect airlines
        # African carriers (Travelport) don't support this
        raise NotImplementedError("Duffel provider not yet implemented")
    
    def close(self) -> None:
        self._http.close()
