"""
Global settings loaded from environment variables.
Centralizes all configuration in one place for reproducibility.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


def _get_secret(name: str, default: str = "") -> str:
    """Read config from env first, then Streamlit secrets when available."""
    value = os.getenv(name)
    if value:
        return value

    try:
        import streamlit as st

        secret = st.secrets.get(name)
        if secret is not None:
            return str(secret)
    except Exception:
        pass

    return default

PROJECT_ROOT = Path(__file__).parent


@dataclass
class Settings:
    """Application settings — single source of truth."""

    # Cloudflare Browser Rendering
    cf_account_id: str = field(default_factory=lambda: _get_secret("CF_ACCOUNT_ID"))
    cf_api_token: str = field(default_factory=lambda: _get_secret("CF_API_TOKEN"))
    cf_base_url: str = field(init=False)

    # Scraping behavior
    scrape_delay_seconds: float = field(
        default_factory=lambda: float(_get_secret("SCRAPE_DELAY_SECONDS", "8"))
    )
    max_retries: int = field(
        default_factory=lambda: int(_get_secret("MAX_RETRIES", "3"))
    )
    request_timeout: int = field(
        default_factory=lambda: int(_get_secret("REQUEST_TIMEOUT", "60"))
    )

    # Paths
    output_dir: Path = field(
        default_factory=lambda: PROJECT_ROOT / _get_secret("OUTPUT_DIR", "data")
    )
    raw_data_dir: Path = field(init=False)
    processed_data_dir: Path = field(init=False)
    reports_dir: Path = field(init=False)
    assets_dir: Path = field(init=False)

    # Logging
    log_level: str = field(
        default_factory=lambda: _get_secret("LOG_LEVEL", "INFO")
    )

    def __post_init__(self):
        self.cf_base_url = (
            f"https://api.cloudflare.com/client/v4/accounts/{self.cf_account_id}/browser-rendering"
        )
        self.raw_data_dir = self.output_dir / "raw"
        self.processed_data_dir = self.output_dir / "processed"
        self.reports_dir = PROJECT_ROOT / "reports"
        self.assets_dir = PROJECT_ROOT / "assets"

        # Ensure directories exist
        for dir_path in [
            self.raw_data_dir,
            self.processed_data_dir,
            self.reports_dir,
            self.assets_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def validate(self) -> list[str]:
        """Return list of configuration errors (empty = valid)."""
        errors = []
        if not self.cf_account_id:
            errors.append("CF_ACCOUNT_ID not set in .env")
        if not self.cf_api_token:
            errors.append("CF_API_TOKEN not set in .env")
        return errors


# Singleton instance
settings = Settings()
