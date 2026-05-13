#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"


def read_latest_url(path: Path) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for line in reversed(lines):
        if "tunneled with tls termination" not in line:
            continue
        if "https://" not in line:
            continue
        return f"https://{line.rsplit('https://', 1)[-1].strip()}"
    return ""


result = {
    "app": read_latest_url(LOG_DIR / "app-tunnel.log"),
    "admin": read_latest_url(LOG_DIR / "admin-tunnel.log"),
}

print(json.dumps(result, ensure_ascii=False, indent=2))
