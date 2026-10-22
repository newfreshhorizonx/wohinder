"""Load profiles from profiles/*.yaml and add contact details from .env."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from .models import Profile

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILES_DIR = REPO_ROOT / "profiles"
ENV_FILE = REPO_ROOT / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    """Minimal .env reader: KEY=value lines; existing environment variables win."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def load_profile(path: Path) -> Profile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    profile = Profile(**data)
    prefix = profile.id.upper()
    profile.contact_email = os.environ.get(f"{prefix}_EMAIL") or None
    profile.contact_phone = os.environ.get(f"{prefix}_PHONE") or None
    return profile


def load_profiles(directory: Path = PROFILES_DIR) -> dict[str, Profile]:
    load_env()
    profiles = [load_profile(p) for p in sorted(directory.glob("*.yaml"))]
    return {p.id: p for p in profiles}
