"""ExpertFlyer seat availability provider."""

from .scraper import (
    FlightAvailability,
    FareAvailability,
    FARE_CLASSES,
    search_and_display,
    extract_results_from_page,
    parse_availability_string,
)

from .browser import (
    login,
    ensure_logged_in,
    search_availability,
)

__all__ = [
    "FlightAvailability",
    "FareAvailability",
    "FARE_CLASSES",
    "search_and_display",
    "extract_results_from_page",
    "parse_availability_string",
    "login",
    "ensure_logged_in",
    "search_availability",
]
