"""Award Travel Finder adapter — high-level functions."""

from typing import Any, Optional

from .client import ATFClient

# Airline name shortcuts → API enum value
AIRLINE_MAP = {
    "british_airways": "british_airways",
    "ba": "british_airways",
    "british": "british_airways",
    "qatar_airways": "qatar_airways",
    "qatar": "qatar_airways",
    "qr": "qatar_airways",
    "cathay_pacific": "cathay_pacific",
    "cathay": "cathay_pacific",
    "cx": "cathay_pacific",
}

# Display names
AIRLINE_DISPLAY = {
    "british_airways": "British Airways",
    "qatar_airways": "Qatar Airways",
    "cathay_pacific": "Cathay Pacific",
}


def resolve_airline(name: str) -> str:
    """Resolve airline shortcut to API enum value."""
    key = name.lower().strip().replace(" ", "_")
    if key in AIRLINE_MAP:
        return AIRLINE_MAP[key]
    raise ValueError(
        f"Unknown airline: {name}. "
        f"Supported: {', '.join(sorted(set(AIRLINE_MAP.values())))}"
    )


def display_name(airline: str) -> str:
    return AIRLINE_DISPLAY.get(airline, airline.replace("_", " ").title())


class ATFAdapter:
    """High-level interface to AwardTravelFinder."""

    def __init__(self, api_key: Optional[str] = None):
        self._client = ATFClient(api_key=api_key)

    def list_airlines(self) -> Any:
        return self._client.call_tool("list_supported_airlines")

    def get_airports(self, airline: str) -> Any:
        return self._client.call_tool("get_airports", {"airline": resolve_airline(airline)})

    def search_daily(self, airline: str, origin: str, dest: str, date: str) -> Any:
        return self._client.call_tool("search_availability", {
            "airline": resolve_airline(airline),
            "departure_code": origin.upper(),
            "arrival_code": dest.upper(),
            "date": date,
        })

    def search_monthly(self, airline: str, origin: str, dest: str, month: str) -> Any:
        return self._client.call_tool("search_monthly_availability", {
            "airline": resolve_airline(airline),
            "departure_code": origin.upper(),
            "arrival_code": dest.upper(),
            "date": month,
        })

    def get_pricing(self, airline: str, origin: str, dest: str) -> Any:
        return self._client.call_tool("get_pricing", {
            "airline": resolve_airline(airline),
            "departure_code": origin.upper(),
            "arrival_code": dest.upper(),
        })

    def list_programs(self) -> Any:
        return self._client.call_tool("list_programs")

    def get_program_rates(self, program: str) -> Any:
        return self._client.call_tool("get_program_rates", {"program": program})

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
