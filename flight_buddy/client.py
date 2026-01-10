"""Amadeus API client."""

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

from .auth import AmadeusAuth


class AmadeusError(Exception):
    """Amadeus API error."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[list] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or []


class AmadeusClient:
    """Client for Amadeus Self-Service APIs."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        # Load from environment if not provided
        load_dotenv()
        
        self.api_key = api_key or os.getenv("AMADEUS_API_KEY")
        self.api_secret = api_secret or os.getenv("AMADEUS_API_SECRET")
        self.base_url = (base_url or os.getenv("AMADEUS_BASE_URL", "https://test.api.amadeus.com")).rstrip("/")
        
        if not self.api_key or not self.api_secret:
            raise AmadeusError("AMADEUS_API_KEY and AMADEUS_API_SECRET required")
        
        self._auth = AmadeusAuth(self.api_key, self.api_secret, self.base_url)
        self._http = httpx.Client(timeout=30.0)
    
    def _headers(self) -> dict:
        """Get headers with current auth token."""
        return {
            "Authorization": f"Bearer {self._auth.get_token()}",
            "Accept": "application/vnd.amadeus+json",
        }
    
    def _handle_error(self, response: httpx.Response) -> None:
        """Handle API error responses."""
        if response.is_success:
            return
        
        try:
            data = response.json()
            errors = data.get("errors", [])
            if errors:
                msg = errors[0].get("detail", errors[0].get("title", "Unknown error"))
                raise AmadeusError(msg, response.status_code, errors)
        except (ValueError, KeyError):
            pass
        
        response.raise_for_status()
    
    def get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Make GET request to Amadeus API."""
        url = f"{self.base_url}{endpoint}"
        response = self._http.get(url, params=params, headers=self._headers())
        self._handle_error(response)
        return response.json()
    
    def post(self, endpoint: str, json: Optional[dict] = None) -> dict:
        """Make POST request to Amadeus API."""
        url = f"{self.base_url}{endpoint}"
        response = self._http.post(url, json=json, headers=self._headers())
        self._handle_error(response)
        return response.json()
    
    # ─────────────────────────────────────────────────────────────
    # Flight APIs
    # ─────────────────────────────────────────────────────────────
    
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
        currency: Optional[str] = None,
    ) -> dict:
        """
        Search for flight offers.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Date in YYYY-MM-DD format
            adults: Number of adult passengers (1-9)
            cabin: Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
            non_stop: Only direct flights
            airlines: Include only these airlines (IATA codes)
            exclude_airlines: Exclude these airlines
            max_results: Maximum number of results
            currency: Currency code for prices
        
        Returns:
            API response with flight offers
        """
        params = {
            "originLocationCode": origin.upper(),
            "destinationLocationCode": destination.upper(),
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
        }
        
        if cabin:
            params["travelClass"] = cabin.upper()
        if non_stop:
            params["nonStop"] = "true"
        if airlines:
            params["includedAirlineCodes"] = ",".join(airlines)
        if exclude_airlines:
            params["excludedAirlineCodes"] = ",".join(exclude_airlines)
        if currency:
            params["currencyCode"] = currency.upper()
        
        return self.get("/v2/shopping/flight-offers", params)
    
    def get_flight_schedule(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
    ) -> dict:
        """
        Get flight schedule by flight number.
        
        Args:
            carrier_code: 2-letter IATA airline code (e.g., "EK")
            flight_number: Flight number (e.g., "766")
            departure_date: Date in YYYY-MM-DD format
        
        Returns:
            API response with flight schedule
        """
        params = {
            "carrierCode": carrier_code.upper(),
            "flightNumber": flight_number,
            "scheduledDepartureDate": departure_date,
        }
        return self.get("/v2/schedule/flights", params)
    
    def get_flight_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        departure_time: Optional[str] = None,
        carrier_code: Optional[str] = None,
        flight_number: Optional[str] = None,
    ) -> dict:
        """
        Get seat availability by cabin class.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Date in YYYY-MM-DD format
            departure_time: Time in HH:MM:SS format (optional)
            carrier_code: Filter by airline (optional)
            flight_number: Filter by flight number (optional)
        
        Returns:
            API response with availability data
        """
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
        
        return self.post("/v1/shopping/availability/flight-availabilities", body)
    
    def get_seat_map(self, flight_offer: dict) -> dict:
        """
        Get seat map for a flight offer.
        
        Args:
            flight_offer: A flight offer from search_flights()
        
        Returns:
            API response with seat map data
        """
        body = {"data": [flight_offer]}
        return self.post("/v1/shopping/seatmaps", body)
    
    def close(self) -> None:
        """Close HTTP client."""
        self._http.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
