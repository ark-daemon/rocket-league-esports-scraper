"""Smoke tests for packaging and settings defaults."""

from rocketleague_scraper import __version__
from rocketleague_scraper.config import Settings


def test_version():
    assert __version__


def test_settings_defaults_without_env():
    settings = Settings()
    assert "blast.tv" in str(settings.blast_base_url)
    assert "liquipedia.net" in str(settings.liquipedia_base_url)
    assert settings.user_agent
    assert settings.blast_tournament_slugs
