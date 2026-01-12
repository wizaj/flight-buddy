"""Legacy client module - re-exports for backward compatibility."""

# Re-export from new location for backward compatibility
from .providers.amadeus.adapter import AmadeusProvider as AmadeusClient
from .providers.base import ProviderError as AmadeusError

__all__ = ["AmadeusClient", "AmadeusError"]
