import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    LOGO_DEV_KEY: str = os.getenv("LOGO_DEV_KEY", "")
    LOGO_NAME_SALT: str = os.getenv("LOGO_NAME_SALT", "")

    # Logos / Storage
    BUCKET_NAME: str = os.getenv("LOGO_BUCKET", "logos")  # default 'logos'
    LOGO_SIZE: tuple[int, int] = (32, 32)
    HTTP_TIMEOUT: int = 10

    # Logo refresh policy (~6 months)
    REFRESH_AFTER_DAYS: int = int(os.getenv("LOGO_REFRESH_DAYS", "182"))

    # EFTS / SEC fetch
    USER_AGENT: str = os.getenv("SEC_USER_AGENT", "youremail@example.com")
    PAGE_SIZE: int = 100
    RATE_LIMIT: float = 0.5
    MAX_RETRIES: int = 3

    # Forms
    FORMS: tuple[str, ...] = (
        "S-1", "F-1", "S-1/A", "F-1/A", "424B1", "424B4", "S-1MEF", "F-1MEF", "RW"
    )
    INITIAL_FORMS: set[str] = frozenset({"S-1", "F-1"})

    def validate(self) -> None:
        missing = []
        if not self.SUPABASE_URL: missing.append("SUPABASE_URL")
        if not self.SUPABASE_SERVICE_ROLE_KEY: missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not self.LOGO_DEV_KEY: missing.append("LOGO_DEV_KEY")
        if not self.LOGO_NAME_SALT: missing.append("LOGO_NAME_SALT")
        if missing:
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

settings = Settings()
settings.validate()