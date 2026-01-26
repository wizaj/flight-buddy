#!/usr/bin/env python3
"""
ExpertFlyer browser automation using agent-browser.

Handles login, session management, and navigation.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from flight-buddy directory
_env_path = Path(__file__).parent.parent.parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

# Cache locations
CACHE_DIR = Path.home() / ".cache" / "flight-buddy"
SESSION_FILE = CACHE_DIR / "ef-session.json"
BROWSER_PROFILE = CACHE_DIR / "ef-browser-profile"

# ExpertFlyer URLs
EF_BASE = "https://www.expertflyer.com"
EF_LOGIN = f"{EF_BASE}/login"
EF_SEAT_AVAIL = f"{EF_BASE}/seatAvailability"


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)


def run_browser(cmd: str, timeout: int = 60) -> str:
    """Run agent-browser command with persistent profile."""
    ensure_cache_dir()
    try:
        # Use persistent profile to maintain login session
        full_cmd = f"agent-browser --profile {BROWSER_PROFILE} {cmd}"
        result = subprocess.run(
            full_cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        output = result.stdout + result.stderr
        return output
    except subprocess.TimeoutExpired:
        return "ERROR: Command timed out"
    except Exception as e:
        return f"ERROR: {e}"


def is_logged_in() -> bool:
    """Check if we're currently logged into ExpertFlyer."""
    # Take a snapshot and look for login indicators
    output = run_browser("snapshot -c")
    
    # If we see "Log Out" or the user menu, we're logged in
    if "Log Out" in output or "My Account" in output:
        return True
    # If we see "Log In" or login form, we're not
    if "Log In" in output or "Sign In" in output or "Password" in output:
        return False
    
    # Default to not logged in
    return False


def get_credentials() -> tuple[str, str]:
    """Get ExpertFlyer credentials from environment."""
    email = os.environ.get("EXPERTFLYER_EMAIL", "")
    password = os.environ.get("EXPERTFLYER_PASSWORD", "")
    
    if not email or not password:
        raise ValueError(
            "ExpertFlyer credentials not found. Set EXPERTFLYER_EMAIL and "
            "EXPERTFLYER_PASSWORD in ~/.zshrc or .env"
        )
    
    return email, password


def save_session():
    """Save current session state (cookies via browser profile)."""
    ensure_cache_dir()
    session_data = {
        "logged_in_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(hours=24)).isoformat(),
    }
    SESSION_FILE.write_text(json.dumps(session_data, indent=2))


def load_session() -> Optional[dict]:
    """Load session state if valid."""
    if not SESSION_FILE.exists():
        return None
    
    try:
        data = json.loads(SESSION_FILE.read_text())
        expires = datetime.fromisoformat(data.get("expires_at", ""))
        if datetime.now() < expires:
            return data
    except (json.JSONDecodeError, ValueError):
        pass
    
    return None


def login(force: bool = False) -> bool:
    """
    Log into ExpertFlyer via Auth0.
    
    Args:
        force: Force re-login even if session exists
        
    Returns:
        True if login successful
    """
    # Check if we have a valid session
    if not force and load_session():
        # Quick check if still logged in
        run_browser(f"open {EF_BASE}")
        time.sleep(2)
        if is_logged_in():
            return True
    
    email, password = get_credentials()
    
    print("🔐 Logging into ExpertFlyer...", file=sys.stderr)
    
    # Navigate to homepage and click Sign In (Auth0 redirect)
    output = run_browser(f'open "{EF_BASE}"')
    if "ERROR" in output:
        print(f"Failed to open homepage: {output}", file=sys.stderr)
        return False
    
    time.sleep(2)
    
    # Click Sign In link to trigger Auth0 redirect
    run_browser('click "Sign In"')
    time.sleep(3)
    
    # Now on Auth0 login page (auth.expertflyer.com)
    # Get snapshot to find form refs
    snapshot = run_browser("snapshot -i -c")
    
    # Auth0 form has Email and Password textboxes
    # Fill email
    run_browser(f'fill @e2 "{email}"')
    time.sleep(0.3)
    
    # Fill password
    run_browser(f'fill @e3 "{password}"')
    time.sleep(0.3)
    
    # Click Log In button
    run_browser('click @e5')
    
    # Wait for Auth0 callback and redirect
    time.sleep(4)
    
    # Check if login succeeded
    if is_logged_in():
        print("✅ Logged in successfully", file=sys.stderr)
        save_session()
        return True
    
    # Fallback: try clicking by text
    run_browser('click "Log In"')
    time.sleep(3)
    
    if is_logged_in():
        print("✅ Logged in successfully", file=sys.stderr)
        save_session()
        return True
    
    print("❌ Login failed", file=sys.stderr)
    return False


def navigate_to_seat_availability() -> bool:
    """Navigate to the Seat Availability search page."""
    output = run_browser(f'navigate "{EF_SEAT_AVAIL}"')
    time.sleep(2)
    
    # Verify we're on the right page
    snapshot = run_browser("snapshot -c")
    
    if "Seat Availability" in snapshot or "Origin" in snapshot:
        return True
    
    # May need to click through menu
    run_browser('click "Seat Availability"')
    time.sleep(2)
    
    return True


def fill_search_form(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
) -> bool:
    """
    Fill the Seat Availability search form.
    
    Args:
        origin: 3-letter airport code
        destination: 3-letter airport code  
        date: YYYY-MM-DD format
        airline: Optional 2-letter airline code
        
    Returns:
        True if form filled successfully
    """
    # Get snapshot to understand form structure
    snapshot = run_browser("snapshot -i -c")
    
    # Clear and fill origin
    # ExpertFlyer uses autocomplete inputs
    run_browser('click @origin')
    time.sleep(0.3)
    run_browser('type @origin ""')  # Clear
    run_browser(f'type @origin "{origin}"')
    time.sleep(0.5)
    # Click first autocomplete suggestion
    run_browser('press Enter')
    time.sleep(0.3)
    
    # Clear and fill destination
    run_browser('click @destination')
    time.sleep(0.3)
    run_browser(f'type @destination "{destination}"')
    time.sleep(0.5)
    run_browser('press Enter')
    time.sleep(0.3)
    
    # Fill date - format depends on locale settings
    # ExpertFlyer typically uses MM/DD/YYYY
    from datetime import datetime as dt
    parsed_date = dt.strptime(date, "%Y-%m-%d")
    formatted_date = parsed_date.strftime("%m/%d/%Y")
    
    run_browser('click @date')
    time.sleep(0.3)
    # Select all and replace
    run_browser('press Control+a')
    run_browser(f'type @date "{formatted_date}"')
    time.sleep(0.3)
    
    # If airline specified, fill that too
    if airline:
        run_browser(f'type @airline "{airline}"')
        time.sleep(0.3)
    
    return True


def submit_search() -> bool:
    """Submit the search form and wait for results."""
    # Click search button
    run_browser('click @search')
    
    # Wait for results to load
    time.sleep(3)
    
    # Check for results table
    snapshot = run_browser("snapshot -c")
    
    # Look for indicators that results loaded
    if "results" in snapshot.lower() or "availability" in snapshot.lower():
        return True
    
    # Try clicking any "Search" button by text
    run_browser('click "Search"')
    time.sleep(3)
    
    return True


def ensure_browser_ready() -> bool:
    """Ensure browser is ready with our profile."""
    ensure_cache_dir()
    
    # Close any existing browser to ensure we use our profile
    run_browser("close")
    time.sleep(1)
    
    # Open ExpertFlyer with our persistent profile
    output = run_browser(f'--headed open "{EF_BASE}"')
    if "ERROR" in output:
        print(f"Failed to start browser: {output}", file=sys.stderr)
        return False
    
    time.sleep(2)
    return True


def ensure_logged_in() -> bool:
    """Ensure we're logged in, logging in if necessary."""
    # Start browser with persistent profile
    if not ensure_browser_ready():
        return False
    
    # Check if already logged in (session persisted in profile)
    if is_logged_in():
        print("✅ Already logged in (session restored)", file=sys.stderr)
        save_session()
        return True
    
    return login()


def build_search_url(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
    alliance: str = "none",
    exclude_codeshares: bool = False,
) -> str:
    """Build direct ExpertFlyer search results URL."""
    from urllib.parse import quote
    
    # Format date as ISO with time
    # Input: YYYY-MM-DD, Output: YYYY-MM-DDT00:00
    date_param = f"{date}T00:00"
    
    params = [
        f"origin={origin.upper()}",
        f"destination={destination.upper()}",
        f"departureDateTime={quote(date_param)}",
        f"alliance={alliance}",
        f"excludeCodeshares={'true' if exclude_codeshares else 'false'}",
        "pcc=USA+%28Default%29",
        "resultsDisplay=tabbed",
    ]
    
    if airline:
        params.append(f"airLineCodes={airline.upper()}")
    
    return f"{EF_BASE}/air/availability/results?{'&'.join(params)}"


def search_availability(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
) -> str:
    """
    Complete flow: ensure logged in → navigate directly to results URL.
    
    Uses direct URL navigation instead of form filling (much more reliable).
    
    Returns the page snapshot for parsing by scraper.py
    """
    # Ensure we're logged in
    if not ensure_logged_in():
        raise RuntimeError("Failed to log into ExpertFlyer")
    
    # Build and navigate to results URL directly
    url = build_search_url(origin, destination, date, airline)
    print(f"🔗 {url}", file=sys.stderr)
    
    output = run_browser(f'navigate "{url}"')
    if "ERROR" in output:
        raise RuntimeError(f"Navigation failed: {output}")
    
    # Wait for results to load
    time.sleep(4)
    
    # Return page snapshot for parsing
    return run_browser("snapshot -c")


if __name__ == "__main__":
    # Quick test
    import argparse
    
    parser = argparse.ArgumentParser(description="ExpertFlyer browser automation")
    parser.add_argument("action", choices=["login", "search", "check"])
    parser.add_argument("--origin", "-o")
    parser.add_argument("--destination", "-d") 
    parser.add_argument("--date")
    parser.add_argument("--airline", "-a")
    parser.add_argument("--force", "-f", action="store_true")
    
    args = parser.parse_args()
    
    if args.action == "login":
        success = login(force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.action == "check":
        # Check login status
        run_browser(f"open {EF_BASE}")
        time.sleep(2)
        logged_in = is_logged_in()
        print(f"Logged in: {logged_in}")
        sys.exit(0 if logged_in else 1)
    
    elif args.action == "search":
        if not all([args.origin, args.destination, args.date]):
            print("--origin, --destination, and --date required for search")
            sys.exit(1)
        
        snapshot = search_availability(
            args.origin,
            args.destination,
            args.date,
            args.airline
        )
        print(snapshot)
