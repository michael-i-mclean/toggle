import os
import json
import tempfile
import asyncio
from typing import Dict


def _save_sync(path: str, data: Dict[str, bool]) -> None:
    """
    Synchronously and atomically write `data` (a dict) to `path`.
    Uses a temporary file in the same directory and os.replace for atomicity.
    """
    dirpath = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(dir=dirpath)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def _load_sync(path: str) -> Dict[str, bool]:
    """
    Synchronously load toggles from `path`. Returns an empty dict if the file
    does not exist or contains invalid JSON.
    """
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return {str(k): bool(v) for k, v in data.items()}
    except (OSError, json.JSONDecodeError):
        # If the file is corrupt/unreadable, return empty store to avoid crashing.
        return {}
    return {}


async def save(path: str, data: Dict[str, bool]) -> None:
    """Async wrapper that offloads the sync write to a thread."""
    await asyncio.to_thread(_save_sync, path, data)


async def load(path: str) -> Dict[str, bool]:
    """Async wrapper that offloads the sync load to a thread."""
    return await asyncio.to_thread(_load_sync, path)
