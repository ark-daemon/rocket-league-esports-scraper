"""Runtime configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from pydantic import HttpUrl, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(v: object) -> list[str] | object:
    """Parse comma-separated env strings; empty string → empty list."""
    if v is None:
        return []
    if isinstance(v, str):
        text = v.strip()
        if not text or text in {"[]", '""', "''"}:
            return []
        return [x.strip() for x in text.split(",") if x.strip()]
    return v


class Settings(BaseSettings):
    """Application settings loaded from environment or `.env`."""

    model_config = SettingsConfigDict(env_prefix="RL_", env_file=".env", extra="ignore")

    db_path: Path = Path("rocketleague.db")
    export_dir: Path = Path("exports")
    log_dir: Path = Path("logs")

    blast_base_url: HttpUrl = "https://blast.tv/rl"
    blast_api_base_url: HttpUrl = "https://api.blast.tv"
    liquipedia_base_url: HttpUrl = "https://liquipedia.net/rocketleague"
    # NoDecode: empty env values must not be JSON-decoded as complex types.
    drekt_csv_urls: Annotated[tuple[HttpUrl, ...], NoDecode] = ()

    http_timeout_seconds: float = 30.0
    blast_rate_limit_seconds: float = 0.75
    liquipedia_rate_limit_seconds: float = 2.0
    spreadsheet_rate_limit_seconds: float = 0.25
    max_concurrency: int = 6
    blast_fingerprint_seed: int = 42069
    blast_probe_deep_stats: bool = False
    blast_max_discovered_tournaments: int = 16

    user_agent: str = (
        "RocketLeagueResearchBot/0.1 "
        "(+https://github.com/ark-daemon/rocket-league-scraper; contact: you@example.com)"
    )

    rlcs_regions: Annotated[tuple[str, ...], NoDecode] = (
        "NA",
        "EU",
        "SAM",
        "OCE",
        "MENA",
        "APAC",
        "SSA",
    )
    blast_tournament_slugs: Annotated[tuple[str, ...], NoDecode] = ("rlcs-world-championship-2026",)
    liquipedia_seed_pages: Annotated[tuple[str, ...], NoDecode] = (
        "Rocket_League_Championship_Series/2026",
        "Rocket_League_Championship_Series/2025",
        "Transfers",
    )

    @field_validator(
        "drekt_csv_urls",
        "blast_tournament_slugs",
        "liquipedia_seed_pages",
        "rlcs_regions",
        mode="before",
    )
    @classmethod
    def _csv_fields(cls, v: object) -> list[str] | object:
        return _split_csv(v)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
