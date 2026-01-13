"""Abstract base class for flight data providers."""

from abc import ABC, abstractmethod
from typing import Optional

from ..models import FlightOffer, FlightSchedule, FlightAvailability, SeatMap


class ProviderError(Exception):
    """Base exception for provider errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[list] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or []


class FlightProvider(ABC):
    """Abstract interface for flight data providers.
    
    Implementations must convert provider-specific responses into
    the common models defined in models.py.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'amadeus', 'duffel')."""
        pass
    
    @abstractmethod
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
        """Search for flight offers.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Date in YYYY-MM-DD format
            return_date: Return date for round-trip (YYYY-MM-DD, optional)
            adults: Number of adult passengers (1-9)
            cabin: Cabin class (ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST)
            non_stop: Only direct flights
            airlines: Include only these airlines (IATA codes)
            exclude_airlines: Exclude these airlines
            max_results: Maximum number of results
            currency: Currency code for prices
        
        Returns:
            List of flight offers
        """
        pass
    
    @abstractmethod
    def get_flight_schedule(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
    ) -> list[FlightSchedule]:
        """Get flight schedule by flight number.
        
        Args:
            carrier_code: 2-letter IATA airline code (e.g., "EK")
            flight_number: Flight number (e.g., "766")
            departure_date: Date in YYYY-MM-DD format
        
        Returns:
            List of flight schedules (usually one)
        """
        pass
    
    @abstractmethod
    def get_flight_availability(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        departure_time: Optional[str] = None,
        carrier_code: Optional[str] = None,
        flight_number: Optional[str] = None,
    ) -> list[FlightAvailability]:
        """Get seat availability by cabin class.
        
        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Date in YYYY-MM-DD format
            departure_time: Time in HH:MM:SS format (optional)
            carrier_code: Filter by airline (optional)
            flight_number: Filter by flight number (optional)
        
        Returns:
            List of flight availability info
        """
        pass
    
    @abstractmethod
    def get_seat_map(
        self,
        carrier_code: str,
        flight_number: str,
        departure_date: str,
        origin: str,
        destination: str,
    ) -> Optional[SeatMap]:
        """Get seat map for a flight.
        
        Args:
            carrier_code: 2-letter IATA airline code
            flight_number: Flight number
            departure_date: Date in YYYY-MM-DD format
            origin: Origin airport IATA code
            destination: Destination airport IATA code
        
        Returns:
            Seat map or None if unavailable
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close any open connections."""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
