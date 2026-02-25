#!/usr/bin/env python3
"""
ExpertFlyer browser automation using agent-browser.

Async version with proper timeout handling.
"""

import asyncio
import json
import os
import sys
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

# Timeouts (seconds)
CMD_TIMEOUT = 30  # Per-command timeout
LOGIN_TIMEOUT = 60  # Total login flow timeout
SEARCH_TIMEOUT = 90  # Total search flow timeout


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    BROWSER_PROFILE.mkdir(parents=True, exist_ok=True)


async def run_browser(cmd: str, timeout: int = CMD_TIMEOUT, headed: bool = False) -> str:
    """Run agent-browser command asynchronously."""
    ensure_cache_dir()
    try:
        headed_flag = "--headed " if headed else ""
        full_cmd = f"agent-browser {headed_flag}--profile {BROWSER_PROFILE} {cmd}"
        proc = await asyncio.create_subprocess_shell(
            full_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(),
            timeout=timeout
        )
        return (stdout.decode() + stderr.decode()).strip()
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except:
            pass
        return "ERROR: Command timed out"
    except Exception as e:
        return f"ERROR: {e}"


async def is_logged_in() -> bool:
    """Check if we're currently logged into ExpertFlyer."""
    output = await run_browser("snapshot -c")
    
    # If we see user menu or welcome message, we're logged in
    if "Wiza" in output or "My Account" in output or "Welcome" in output:
        return True
    # If we see login indicators, we're not
    if "Sign In" in output or "Log In" in output or "Password" in output:
        return False
    
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
    """Save current session state."""
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


async def login(force: bool = False) -> bool:
    """Log into ExpertFlyer via Auth0."""
    
    async def _do_login():
        # Check if we have a valid session
        if not force and load_session():
            await run_browser(f'open "{EF_BASE}"')
            await asyncio.sleep(2)
            if await is_logged_in():
                return True
        
        email, password = get_credentials()
        
        print("🔐 Logging into ExpertFlyer...", file=sys.stderr)
        
        # Navigate to homepage
        output = await run_browser(f'open "{EF_BASE}"')
        if "ERROR" in output:
            print(f"Failed to open homepage: {output}", file=sys.stderr)
            return False
        
        await asyncio.sleep(2)
        
        # Click Sign In
        await run_browser('click "Sign In"')
        await asyncio.sleep(3)
        
        # Get snapshot to find form refs
        snapshot = await run_browser("snapshot -i -c")
        
        # Find email/password refs dynamically
        email_ref = "@e3"  # Default
        pass_ref = "@e4"   # Default
        login_ref = "@e6"  # Default
        
        if 'textbox "Email"' in snapshot:
            # Parse refs from snapshot
            for line in snapshot.split('\n'):
                if 'textbox "Email"' in line and '[ref=' in line:
                    email_ref = '@' + line.split('[ref=')[1].split(']')[0]
                elif 'textbox "Password"' in line and '[ref=' in line:
                    pass_ref = '@' + line.split('[ref=')[1].split(']')[0]
                elif 'button "Log In"' in line and '[ref=' in line:
                    login_ref = '@' + line.split('[ref=')[1].split(']')[0]
        
        # Fill credentials
        await run_browser(f'fill {email_ref} "{email}"')
        await asyncio.sleep(0.5)
        await run_browser(f'fill {pass_ref} "{password}"')
        await asyncio.sleep(0.5)
        
        # Click login
        await run_browser(f'click {login_ref}')
        await asyncio.sleep(4)
        
        # Check success
        if await is_logged_in():
            print("✅ Logged in successfully", file=sys.stderr)
            save_session()
            return True
        
        # Fallback: try clicking by text
        await run_browser('click "Log In"')
        await asyncio.sleep(3)
        
        if await is_logged_in():
            print("✅ Logged in successfully", file=sys.stderr)
            save_session()
            return True
        
        print("❌ Login failed", file=sys.stderr)
        return False
    
    try:
        return await asyncio.wait_for(_do_login(), timeout=LOGIN_TIMEOUT)
    except asyncio.TimeoutError:
        print("❌ Login timed out", file=sys.stderr)
        return False


async def ensure_browser_ready() -> bool:
    """Ensure browser is ready with our profile."""
    ensure_cache_dir()
    
    # Close any existing browser
    await run_browser("close", timeout=5)
    await asyncio.sleep(1)
    
    # Open ExpertFlyer (headed mode to avoid CloudFront blocks)
    output = await run_browser(f'open "{EF_BASE}"', headed=True)
    if "ERROR" in output and "403" in output:
        print(f"Failed to start browser: {output}", file=sys.stderr)
        return False
    
    await asyncio.sleep(2)
    return True


async def ensure_logged_in() -> bool:
    """Ensure we're logged in, logging in if necessary."""
    if not await ensure_browser_ready():
        return False
    
    if await is_logged_in():
        print("✅ Already logged in (session restored)", file=sys.stderr)
        save_session()
        return True
    
    return await login()


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


async def search_availability(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
) -> str:
    """
    Complete flow: ensure logged in → navigate to results URL.
    
    Returns the page snapshot for parsing.
    """
    
    async def _do_search():
        # Ensure we're logged in
        if not await ensure_logged_in():
            raise RuntimeError("Failed to log into ExpertFlyer")
        
        # Build and navigate to results URL
        url = build_search_url(origin, destination, date, airline)
        print(f"🔗 {url}", file=sys.stderr)
        
        output = await run_browser(f'navigate "{url}"')
        if "ERROR" in output:
            raise RuntimeError(f"Navigation failed: {output}")
        
        # Wait for results
        await asyncio.sleep(4)
        
        # Return snapshot
        return await run_browser("snapshot -c")
    
    try:
        return await asyncio.wait_for(_do_search(), timeout=SEARCH_TIMEOUT)
    except asyncio.TimeoutError:
        raise RuntimeError("Search timed out")


# Sync wrappers for CLI compatibility
def search_availability_sync(
    origin: str,
    destination: str,
    date: str,
    airline: Optional[str] = None,
) -> str:
    """Synchronous wrapper for search_availability."""
    return asyncio.run(search_availability(origin, destination, date, airline))


def login_sync(force: bool = False) -> bool:
    """Synchronous wrapper for login."""
    return asyncio.run(login(force))


def is_logged_in_sync() -> bool:
    """Synchronous wrapper for is_logged_in."""
    async def _check():
        await run_browser(f'open "{EF_BASE}"')
        await asyncio.sleep(2)
        return await is_logged_in()
    return asyncio.run(_check())


if __name__ == "__main__":
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
        success = login_sync(force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.action == "check":
        logged_in = is_logged_in_sync()
        print(f"Logged in: {logged_in}")
        sys.exit(0 if logged_in else 1)
    
    elif args.action == "search":
        if not all([args.origin, args.destination, args.date]):
            print("--origin, --destination, and --date required for search")
            sys.exit(1)
        
        try:
            snapshot = search_availability_sync(
                args.origin,
                args.destination,
                args.date,
                args.airline
            )
            print(snapshot)
        except RuntimeError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
