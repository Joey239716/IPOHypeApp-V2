# prod/config.py
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


def _truthy(val: str | None) -> bool:
    """Parse common truthy values for env flags."""
    return str(val or "").strip().lower() in {"1", "true", "yes", "y", "on"}


# Always load the .env that sits next to this file (e.g., prod/.env)
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)  # don't override OS envs
# Also allow a CWD .env if you run from inside the package (won't override OS envs)
load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    # --- Required secrets / keys ---
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    LOGO_DEV_KEY: str = os.getenv("LOGO_DEV_KEY", "")
    LOGO_NAME_SALT: str = os.getenv("LOGO_NAME_SALT", "")

    # SEC requires a valid contact email in the UA (we use the same field everywhere)
    SEC_USER_AGENT: str = os.getenv("SEC_USER_AGENT", "")
    USER_AGENT: str = SEC_USER_AGENT  # rest of the code reads USER_AGENT

    # --- Storage / logos ---
    BUCKET_NAME: str = os.getenv("LOGO_BUCKET", "logos")
    LOGO_SIZE: tuple[int, int] = (32, 32)
    HTTP_TIMEOUT: int = int(os.getenv("HTTP_TIMEOUT", "10"))
    REFRESH_AFTER_DAYS: int = int(os.getenv("LOGO_REFRESH_DAYS", "182"))

    # --- EFTS fetch behavior ---
    PAGE_SIZE: int = int(os.getenv("PAGE_SIZE", "100"))
    RATE_LIMIT: float = float(os.getenv("RATE_LIMIT", "0.5"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))

    # --- Safety/testing ---
    DRY_RUN: bool = _truthy(os.getenv("DRY_RUN"))

    # --- Filing filters ---
    FORMS: tuple[str, ...] = (
        "S-1", "F-1", "S-1/A", "F-1/A", "424B1", "424B4", "S-1MEF", "F-1MEF", "RW"
    )
    INITIAL_FORMS: set[str] = frozenset({"S-1", "F-1"})

    def validate(self) -> None:
        missing = [
            k for k in (
                "SUPABASE_URL",
                "SUPABASE_SERVICE_ROLE_KEY",
                "LOGO_DEV_KEY",
                "LOGO_NAME_SALT",
                "SEC_USER_AGENT",
            ) if not getattr(self, k)
        ]
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
        if "@" not in self.SEC_USER_AGENT:
            print("[WARN] SEC_USER_AGENT should include a contact email (per SEC guidance).")


settings = Settings()
settings.validate()
