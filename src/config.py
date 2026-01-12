"""Configuration loader for Flight Buddy."""

import os
from pathlib import Path
from typing import Any

import yaml


# Default config values
DEFAULTS = {
    "provider": "amadeus",
    "amadeus": {
        "base_url": "https://test.api.amadeus.com",
    },
    "duffel": {
        "base_url": "https://api.duffel.com",
    },
    "defaults": {
        "currency": "USD",
        "max_results": 10,
    },
}


def find_config_file() -> Path | None:
    """Find config.yaml in current dir or project root."""
    # Check current directory
    cwd = Path.cwd()
    if (cwd / "config.yaml").exists():
        return cwd / "config.yaml"
    
    # Check src directory parent (project root)
    src_dir = Path(__file__).parent
    project_root = src_dir.parent
    if (project_root / "config.yaml").exists():
        return project_root / "config.yaml"
    
    return None


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml.
    
    Returns default values if no config file exists.
    Environment variable FLIGHT_BUDDY_CONFIG can override config file path.
    """
    config = DEFAULTS.copy()
    
    # Allow env override for config path
    config_path = os.getenv("FLIGHT_BUDDY_CONFIG")
    if config_path:
        path = Path(config_path)
    else:
        path = find_config_file()
    
    if path and path.exists():
        with open(path) as f:
            user_config = yaml.safe_load(f) or {}
        
        # Merge user config with defaults
        config = _deep_merge(config, user_config)
    
    return config


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_default(key: str, fallback: Any = None) -> Any:
    """Get a default value from config.
    
    Args:
        key: Dot-notation key (e.g., "defaults.currency")
        fallback: Fallback if key not found
    
    Returns:
        Config value or fallback
    """
    config = load_config()
    defaults = config.get("defaults", {})
    
    # Support dot notation
    if "." in key:
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return fallback
        return value if value is not None else fallback
    
    return defaults.get(key, fallback)
