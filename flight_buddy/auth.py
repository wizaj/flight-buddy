"""OAuth2 authentication for Amadeus API."""

import time
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class Token:
    """OAuth2 access token with expiry tracking."""
    access_token: str
    expires_at: float  # Unix timestamp
    
    @property
    def is_expired(self) -> bool:
        """Check if token is expired (with 60s buffer)."""
        return time.time() >= (self.expires_at - 60)


class AmadeusAuth:
    """Handles OAuth2 authentication for Amadeus API."""
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "https://test.api.amadeus.com",
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self._token: Optional[Token] = None
    
    def get_token(self) -> str:
        """Get valid access token, refreshing if needed."""
        if self._token is None or self._token.is_expired:
            self._refresh_token()
        return self._token.access_token
    
    def _refresh_token(self) -> None:
        """Fetch new access token from Amadeus."""
        url = f"{self.base_url}/v1/security/oauth2/token"
        
        response = httpx.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        
        data = response.json()
        expires_in = data.get("expires_in", 1799)  # Default ~30 min
        
        self._token = Token(
            access_token=data["access_token"],
            expires_at=time.time() + expires_in,
        )
    
    def invalidate(self) -> None:
        """Force token refresh on next request."""
        self._token = None
