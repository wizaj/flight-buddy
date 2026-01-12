"""Amadeus API provider implementation."""

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from ..base import FlightProvider, ProviderError
from ...models import (
    FlightOffer, FlightSchedule, FlightAvailability, SeatMap,
    parse_flight_offers, parse_flight_schedule, parse_flight_availability, parse_seat_map
)
from .auth import AmadeusAuth


class AmadeusProvider(FlightProvider):
    """Amadeus Self-Service API provider."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        load_dotenv()
        
        self.api_key = api_key or os.getenv("AMADEUS_API_KEY")
        self.api_secret = api_secret or os.getenv("AMADEUS_API_SECRET")
        self.base_url = (base_url or os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")).rstrip("/")
        
        if not self.api_key or not self.api_secret:
            raise ProviderError("AMADEUS_API_KEY and AMADEUS_API_SECRET required")
        
        self._auth = AmadeusAuth(self.api_key, self.api_secret, self.base_url)
        self._http = httpx.Client(timeout=30.0)
    
    @property
    def name(self) -> str:
        return "amadeus"
    
    def _headers(self) -> dict:
        """Get headers with current auth token."""
        return {
            "Authorization": f"Bearer {self._auth.get_token()}",
            "Accept": "application/vnd.amadeus+json",
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Make authenticated request to Amadeus API."""
        url = f"{self.base_url}{endpoint}"
        headers = {**self._headers(), **kwargs.pop("headers", {})}
        
        response = self._http.request(method, url, headers=headers, **kwargs)
        
        if response.status_code == 401:
            # Token expired, refresh and retry
            self._auth.invalidate()
            headers["Authorization"] = f"Bearer {self._auth.get_token()}"
            response = self._http.request(method, url, headers=headers, **kwargs)
        
        if not response.is_success:
            self._handle_error(response)
        
        return response.json()
    
    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error response."""
        try:
            data = response.json()
            errors = data.get("errors", [])
            if errors:
                msg = errors[0].get("detail", errors[0].get("title", "API error"))
                raise ProviderError(msg, response.status_code, errors)
        except (ValueError, KeyError):
            pass
        raise ProviderError(f"HTTP {response.status_code}: {response.text}", response.status_code)
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """GET request."""
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, body: dict) -> dict:
        """POST request with JSON body."""
        return self._request("POST", endpoint, json=body)
    
    # --- FlightProvider interface ---
    
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
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": currency,
            "max": max_results,
        }
        
        if cabin:
            params["travelClass"] = cabin.upper()
        if non_stop:
            params["nonStop"] = "true"
        if airlines:
            params["includedAirlineCodes"] = ",".join(a.upper() for a in airlines)
        if exclude_airlines:
            params["excludedAirlineCodes"] = ",".join(a.upper() for a in exclude_airlines)
        
        response = self.get("/v2/shopping/flight-offers", params)
        return parse_flight_offers(response)
    
    def get_flight_schedule(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
    ) -> list[FlightSchedule]:
        params = {
            "carrierCode": carrier_code.upper(),
            "flightNumber": flight_number,
            "scheduledDepartureDate": departure_date,
        }
        response = self.get("/v2/schedule/flights", params)
        return parse_flight_schedule(response)
    
    def get_flight_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        departure_time: Optional[str] = None,
        carrier_code: Optional[str] = None,
        flight_number: Optional[str] = None,
    ) -> list[FlightAvailability]:
        flight_data = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDateTime": {"date": departure_date},
        }
        
        if departure_time:
            flight_data["departureDateTime"]["time"] = departure_time
        if carrier_code:
            flight_data["carrierCode"] = carrier_code.upper()
        if flight_number:
            flight_data["number"] = flight_number
        
        body = {
            "originDestinations": [{"id": "1", **flight_data}],
            "travelers": [{"id": "1", "travelerType": "ADULT"}],
            "sources": ["GDS"],
        }
        
        response = self.post("/v1/shopping/availability/flight-availabilities", body)
        return parse_flight_availability(response)
    
    def get_seat_map(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
        origin: str,
        destination: str,
    ) -> Optional[SeatMap]:
        # First search for the flight offer
        offers = self.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            max_results=50,
        )
        
        # Find matching offer
        target_flight = f"{carrier_code.upper()}{flight_number}"
        flight_offer = None
        
        for offer in offers:
            for itin in offer.itineraries:
                for seg in itin.segments:
                    if seg.flight_code == target_flight:
                        flight_offer = offer
                        break
        
        if not flight_offer:
            return None
        
        # Need raw offer for seat map API - search again for raw response
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": 1,
            "max": 50,
        }
        raw_response = self.get("/v2/shopping/flight-offers", params)
        
        # Find matching raw offer
        raw_offer = None
        for offer_data in raw_response.get("data", []):
            for itin in offer_data.get("itineraries", []):
                for seg in itin.get("segments", []):
                    code = seg.get("carrierCode", "") + seg.get("number", "")
                    if code == target_flight:
                        raw_offer = offer_data
                        break
        
        if not raw_offer:
            return None
        
        body = {"data": [raw_offer]}
        response = self.post("/v1/shopping/seatmaps", body)
        return parse_seat_map(response)
    
    def close(self) -> None:
        """Close HTTP client."""
        self._http.close()


# Legacy alias for backward compatibility
AmadeusClient = AmadeusProvider
AmadeusError = ProviderError
