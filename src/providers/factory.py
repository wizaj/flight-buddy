"""Provider factory for creating flight data providers."""

from typing import Optional

from .base import FlightProvider, ProviderError
from ..config import load_config


def get_provider(provider_name: Optional[str] = None) -> FlightProvider:
    """Get a flight provider instance.
    
    Args:
        provider_name: Provider name ('amadeus', 'serpapi', 'duffel'). 
                      If None, uses config.yaml setting.
    
    Returns:
        Configured FlightProvider instance
    
    Raises:
        ProviderError: If provider is not supported or misconfigured
    """
    config = load_config()
    name = (provider_name or config.get("provider", "amadeus")).lower()
    
    if name == "amadeus":
        from .amadeus import AmadeusProvider
        amadeus_config = config.get("amadeus", {})
        return AmadeusProvider(
            base_url=amadeus_config.get("base_url"),
        )
    
    elif name == "serpapi":
        from .serpapi import SerpApiProvider
        serpapi_config = config.get("serpapi", {})
        return SerpApiProvider(
            base_url=serpapi_config.get("base_url"),
        )
    
    elif name == "duffel":
        from .duffel import DuffelProvider
        duffel_config = config.get("duffel", {})
        return DuffelProvider(
            base_url=duffel_config.get("base_url"),
        )
    
    else:
        raise ProviderError(f"Unknown provider: {name}. Supported: amadeus, serpapi, duffel")
