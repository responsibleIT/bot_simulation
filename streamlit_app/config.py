"""Configuration and environment variable handling for the Bot Workshop app.

This module loads variables from a `.env` file if present in the project
root and exposes them via module attributes.  It provides sane defaults for
local development but expects these variables to be overridden in production.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Set

# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

# Attempt to load a .env file located two directories up from this file.  This
# allows the app to pick up environment variables from a local .env file
# without requiring the user to install python-dotenv.  If a variable is
# already defined in the environment, it is not overwritten.
_env_path = Path(__file__).resolve().parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if not _line or _line.startswith("#") or "=" not in _line:
            continue
        _key, _val = _line.split("=", 1)
        os.environ.setdefault(_key.strip(), _val.strip())

# ---------------------------------------------------------------------------
# Configuration values
# ---------------------------------------------------------------------------

# Core Appwrite configuration.  These values should be set in the environment
# or .env file.  They fall back to None if not provided.
APPWRITE_ENDPOINT: str | None = os.environ.get("APPWRITE_ENDPOINT")
APPWRITE_PROJECT_ID: str | None = os.environ.get("APPWRITE_PROJECT_ID")
APPWRITE_API_KEY: str | None = os.environ.get("APPWRITE_API_KEY")

# OpenAI configuration.  Without a valid API key the generative functions
# in helpers/openai_utils will return ``None`` and bots will not create content.
OPENAI_API_KEY: str | None = os.environ.get("OPENAI_API_KEY")

# Database and collection identifiers.  Update these values if you change
# collection IDs in the Appwrite dashboard.
DATABASE_ID: str | None = os.environ.get("DATABASE_ID")
BOTS_COLLECTION_ID: str = os.environ.get("BOTS_COLLECTION_ID", "bots")
POSTS_COLLECTION_ID: str = os.environ.get("POSTS_COLLECTION_ID", "posts")
USERS_COLLECTION_ID: str = os.environ.get("USERS_COLLECTION_ID", "users")
COMMENTS_COLLECTION_ID: str = os.environ.get("COMMENTS_COLLECTION_ID", "comments")

# Comma-separated list of admin e‑mail addresses.  These users can access the
# analysis screen to run bots.
_admins = os.environ.get("ADMIN_EMAILS", "")
ADMIN_EMAILS: Set[str] = set(filter(None, [a.strip() for a in _admins.split(",")]))

__all__ = [
    "APPWRITE_ENDPOINT",
    "APPWRITE_PROJECT_ID",
    "APPWRITE_API_KEY",
    "OPENAI_API_KEY",
    "DATABASE_ID",
    "BOTS_COLLECTION_ID",
    "POSTS_COLLECTION_ID",
    "USERS_COLLECTION_ID",
    "COMMENTS_COLLECTION_ID",
    "ADMIN_EMAILS",
]