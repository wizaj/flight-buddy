"""Mileage balance tracking for Flight Buddy."""

import os
from datetime import date
from pathlib import Path
from typing import Optional

import yaml


# Default balances file location
BALANCES_FILE = Path(__file__).parent.parent / "balances.yaml"

# Program display names (matches seatsaero adapter)
PROGRAM_NAMES = {
    "aeroplan": "Aeroplan",
    "united": "United MileagePlus",
    "american": "AAdvantage", 
    "alaska": "Alaska Mileage Plan",
    "delta": "Delta SkyMiles",
    "virginatlantic": "Virgin Atlantic",
    "aerlingus": "Aer Lingus Avios",
    "qantas": "Qantas",
    "velocity": "Velocity",
    "emirates": "Emirates Skywards",
    "etihad": "Etihad Guest",
    "singapore": "KrisFlyer",
    "lifemiles": "LifeMiles",
    "smiles": "Smiles",
    "eurobonus": "SAS EuroBonus",
    "flyingblue": "Flying Blue",
    "connectmiles": "ConnectMiles",
}


def get_balances_path() -> Path:
    """Get path to balances file."""
    env_path = os.getenv("FLIGHT_BUDDY_BALANCES")
    if env_path:
        return Path(env_path)
    return BALANCES_FILE


def load_balances() -> dict:
    """Load balances from YAML file."""
    path = get_balances_path()
    if not path.exists():
        return {"balances": {}}
    
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    
    # Ensure balances key exists and is a dict
    if "balances" not in data or data["balances"] is None:
        data["balances"] = {}
    
    return data


def save_balances(data: dict) -> None:
    """Save balances to YAML file."""
    path = get_balances_path()
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def get_balance(program: str) -> Optional[dict]:
    """Get balance for a specific program."""
    data = load_balances()
    return data.get("balances", {}).get(program.lower())


def get_all_balances() -> dict:
    """Get all balances."""
    data = load_balances()
    return data.get("balances", {})


def update_balance(
    program: str,
    miles: int,
    tier: Optional[str] = None,
    note: Optional[str] = None,
) -> dict:
    """Update balance for a program, tracking history.
    
    Returns the updated balance entry.
    """
    data = load_balances()
    balances = data.setdefault("balances", {})
    
    program_key = program.lower()
    today = date.today().isoformat()
    
    # Get or create entry
    entry = balances.get(program_key, {
        "program": PROGRAM_NAMES.get(program_key, program.title()),
        "miles": 0,
        "history": [],
    })
    
    # Track previous balance
    prev_miles = entry.get("miles", 0)
    delta = miles - prev_miles
    
    # Update current
    entry["miles"] = miles
    entry["updated"] = today
    
    if tier:
        entry["tier"] = tier
    
    # Add to history
    history = entry.setdefault("history", [])
    history_entry = {
        "date": today,
        "miles": miles,
    }
    if delta != 0 and prev_miles > 0:
        history_entry["delta"] = delta
    if note:
        history_entry["note"] = note
    
    history.append(history_entry)
    
    # Keep last 50 history entries
    entry["history"] = history[-50:]
    
    # Save
    balances[program_key] = entry
    save_balances(data)
    
    return entry


def check_affordability(program: str, required_miles: int) -> dict:
    """Check if user can afford a redemption.
    
    Returns:
        {
            "affordable": bool,
            "balance": int,
            "required": int,
            "delta": int,  # positive = surplus, negative = shortfall
            "status": "ok" | "close" | "short"
        }
    """
    balance_data = get_balance(program)
    balance = balance_data.get("miles", 0) if balance_data else 0
    
    delta = balance - required_miles
    
    if delta >= 0:
        status = "ok"
    elif delta >= -10000:  # Within 10k miles
        status = "close"
    else:
        status = "short"
    
    return {
        "affordable": delta >= 0,
        "balance": balance,
        "required": required_miles,
        "delta": delta,
        "status": status,
    }


def format_miles(miles: int) -> str:
    """Format miles with thousands separator."""
    return f"{miles:,}"


def format_delta(delta: int) -> str:
    """Format delta with sign."""
    if delta > 0:
        return f"+{delta:,}"
    return f"{delta:,}"
