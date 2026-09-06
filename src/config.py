"""Loads configuration/secrets from the .env file at the project root."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

META_SYSTEM_USER_TOKEN = os.getenv("META_SYSTEM_USER_TOKEN")
META_APP_ID = os.getenv("META_APP_ID")
META_BUSINESS_ID = os.getenv("META_BUSINESS_ID")

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

OUTPUT_DIR = ROOT_DIR / "output"
CONFIG_DIR = ROOT_DIR / "config"


def require_token() -> str:
    if not META_SYSTEM_USER_TOKEN:
        raise RuntimeError(
            "META_SYSTEM_USER_TOKEN is missing. Check E:\\royal300\\Monthly_Report\\.env"
        )
    return META_SYSTEM_USER_TOKEN
