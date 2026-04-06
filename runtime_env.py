"""Minimal environment-file loader for local/dev and server deploys."""

from __future__ import annotations

import os
from pathlib import Path

from storage import BASE_DIR


_LOADED = False


def load_env_file(env_path: Path | None = None) -> None:
    global _LOADED
    if _LOADED:
        return

    candidate = env_path or (BASE_DIR / ".env")
    if not candidate.exists():
        _LOADED = True
        return

    for raw_line in candidate.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)

    _LOADED = True
