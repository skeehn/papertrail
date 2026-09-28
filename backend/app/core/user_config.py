"""User-editable runtime configuration (API keys entered in Settings).

Keys live in ``~/.papertrail/config.json`` (0600, outside the repo) so that a
fresh clone can be configured entirely from the Settings page — no .env editing
required. Values here take precedence over environment variables, and every
consumer reads them through :func:`get_key` at call time so a key saved in the
UI takes effect without restarting the server.

Nothing here is required: with no config file and no env vars the app still
boots, and Settings reports what is missing.
"""

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("user_config")

CONFIG_DIR = Path(os.environ.get("PAPERTRAIL_CONFIG_DIR", Path.home() / ".papertrail"))
CONFIG_PATH = CONFIG_DIR / "config.json"

# Keys the Settings page can manage. Anything not listed is ignored on write.
MANAGED_KEYS = (
    "OPENAI_API_KEY",
    "OPENAI_BASE_URL",
    "OPENAI_MODEL",
    "PINECONE_API_KEY",
    "PINECONE_INDEX_NAME",
    "PINECONE_HOST",
    "NEO4J_URI",
    "NEO4J_USERNAME",
    "NEO4J_PASSWORD",
    "HELIXDB_API_KEY",
    "HELIXDB_DATABASE",
    "HELIXDB_COLLECTION",
)

# Keys whose values must never be sent back to the browser.
SECRET_KEYS = frozenset({"OPENAI_API_KEY", "PINECONE_API_KEY", "NEO4J_PASSWORD", "HELIXDB_API_KEY"})

_lock = threading.Lock()
_cache: Optional[Dict[str, str]] = None


def _read() -> Dict[str, str]:
    global _cache
    if _cache is not None:
        return _cache
    data: Dict[str, str] = {}
    try:
        if CONFIG_PATH.exists():
            raw = json.loads(CONFIG_PATH.read_text() or "{}")
            if isinstance(raw, dict):
                data = {k: str(v) for k, v in raw.items() if v is not None}
    except Exception as e:  # noqa: BLE001 - never let bad config break boot
        logger.warning(
            "Could not read user config", path=str(CONFIG_PATH), error=str(e)
        )
    _cache = data
    return data


def get_key(name: str, default: str = "") -> str:
    """Resolve a setting: user config → environment/.env → default.

    Read at call time so Settings changes apply without a restart.
    """
    value = _read().get(name)
    if value:
        return value
    env_value = os.environ.get(name)
    if env_value:
        return env_value
    fallback = getattr(settings, name, None)
    if fallback:
        return str(fallback)
    return default


def save_keys(updates: Dict[str, Any]) -> Dict[str, str]:
    """Persist managed keys to ``~/.papertrail/config.json`` (0600).

    An empty string clears a key (falls back to env). Unknown keys are ignored.
    """
    global _cache
    with _lock:
        current = dict(_read())
        for name, value in updates.items():
            if name not in MANAGED_KEYS:
                continue
            if value is None:
                continue
            text = str(value).strip()
            if text:
                current[name] = text
            else:
                current.pop(name, None)

        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(current, indent=2, sort_keys=True))
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:  # pragma: no cover - platform dependent
            pass
        _cache = current
        logger.info("Saved user config", keys=sorted(current.keys()))
        return current


def reload() -> None:
    """Drop the cache so the next read hits disk."""
    global _cache
    _cache = None


def masked_status() -> Dict[str, Any]:
    """Non-secret view of configuration for the Settings UI."""
    out: Dict[str, Any] = {}
    for name in MANAGED_KEYS:
        value = get_key(name)
        if name in SECRET_KEYS:
            out[name] = {"configured": bool(value), "value": ""}
        else:
            out[name] = {"configured": bool(value), "value": value}
    return out
