import os
import json
import logging

logger = logging.getLogger(__name__)

# Search paths for config file
CONFIG_PATHS = [
    os.path.join(os.getcwd(), "config.json"),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json"),
    os.path.expanduser("~/.mikewhisper_config.json"),
]

DEFAULT_CONFIG = {
    "hotkey_cursor": "Ctrl+Space",
    "hotkey_brain": "Fn+Space",
    "daily_brain_url": "http://localhost:4321/api/inbox",
    "offline_queue_path": "~/.mikewhisper_brain_queue.jsonl",
    "model_size": "base.en",
}

def get_config_file_path() -> str:
    """Returns the first existing config file, or default workspace config.json."""
    for path in CONFIG_PATHS:
        normalized = os.path.abspath(path)
        if os.path.exists(normalized):
            return normalized
    return os.path.abspath(CONFIG_PATHS[1])

def load_config() -> dict:
    """
    Loads configuration with precedence:
    1. Environment variables (MIKEWHISPER_HOTKEY_CURSOR, MIKEWHISPER_HOTKEY_BRAIN, etc.)
    2. config.json file
    3. Default configuration
    """
    config = dict(DEFAULT_CONFIG)
    
    # Try loading from config file
    config_file = get_config_file_path()
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                config.update(file_data)
        except Exception as e:
            logger.warning(f"Failed to read config file {config_file}: {e}")

    # Environment variables override file config
    if os.environ.get("MIKEWHISPER_HOTKEY_CURSOR"):
        config["hotkey_cursor"] = os.environ["MIKEWHISPER_HOTKEY_CURSOR"]
    elif os.environ.get("MIKEWHISPER_HOTKEY"):
        config["hotkey_cursor"] = os.environ["MIKEWHISPER_HOTKEY"]

    if os.environ.get("MIKEWHISPER_HOTKEY_BRAIN"):
        config["hotkey_brain"] = os.environ["MIKEWHISPER_HOTKEY_BRAIN"]

    if os.environ.get("DAILY_BRAIN_URL"):
        config["daily_brain_url"] = os.environ["DAILY_BRAIN_URL"]

    return config

def save_config(updates: dict, config_path: str = None) -> str:
    """Saves updated settings to config.json."""
    target_path = config_path or get_config_file_path()
    current = load_config()
    current.update(updates)
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    return target_path
