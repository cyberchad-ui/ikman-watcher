import json
from datetime import datetime, timezone, timedelta
from pathlib import Path


def _state_path(config_path: str) -> Path:
    name = Path(config_path).stem  # e.g. "config" or "config_friend"
    suffix = name[len("config"):] if name.startswith("config") else f"_{name}"
    return Path(f"state/seen{suffix}.json")


def load(config_path: str = "config.yaml") -> dict:
    path = _state_path(config_path)
    if not path.exists():
        return {"first_run_done": False, "last_zero_alert": None, "seen": {}}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"first_run_done": False, "last_zero_alert": None, "seen": {}}


def save(s: dict, config_path: str = "config.yaml") -> None:
    path = _state_path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(s, f, indent=2)


def prune(s: dict, days: int = 60) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    s["seen"] = {
        slug: ts
        for slug, ts in s["seen"].items()
        if datetime.fromisoformat(ts) > cutoff
    }
    return s


def is_first_run(s: dict) -> bool:
    return not s.get("first_run_done", False)


def mark_seen(s: dict, slug: str) -> None:
    s["seen"][slug] = datetime.now(timezone.utc).isoformat()


def is_seen(s: dict, slug: str) -> bool:
    return slug in s["seen"]


def should_send_zero_alert(s: dict) -> bool:
    last = s.get("last_zero_alert")
    if last is None:
        return True
    elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(last)).total_seconds()
    return elapsed > 86400


def mark_zero_alert_sent(s: dict) -> None:
    s["last_zero_alert"] = datetime.now(timezone.utc).isoformat()
