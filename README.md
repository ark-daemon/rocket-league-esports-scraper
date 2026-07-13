# Rocket League Esports Scraper

Async Python 3.11+ scraper for **Rocket League esports data** from:

- [BLAST.tv RL](https://blast.tv/rl) / BLAST API
- [Liquipedia Rocket League](https://liquipedia.net/rocketleague)
- Optional public Google Sheets CSV exports (e.g. community stats)

Covers tournaments, teams, players, matches, rosters, earnings, and advanced stats where available. Data is staged in SQLite and exported to Parquet.

---

## Install

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e ".[dev]"
```

```bash
cp .env.example .env
# Optional: set RL_DREKT_CSV_URLS and a real contact in RL_USER_AGENT
```

Sensible public defaults are built in; `.env` is only required to customize.

## Usage

```bash
rl-scraper scrape all
rl-scraper scrape liquipedia
rl-scraper scrape blast
rl-scraper scrape drekt
rl-scraper export
rl-scraper status
```

## Configuration

All settings use the `RL_` prefix. See `.env.example`.

| Variable | Purpose |
|----------|---------|
| `RL_BLAST_BASE_URL` | BLAST site base |
| `RL_BLAST_API_BASE_URL` | BLAST API base |
| `RL_LIQUIPEDIA_BASE_URL` | Liquipedia RL wiki |
| `RL_DREKT_CSV_URLS` | Optional comma-separated sheet CSV URLs |
| `RL_USER_AGENT` | Identify your bot + contact |

## Testing

```bash
pytest -q
```

## Responsible use

- Keep rate limits conservative (defaults â‰¤ ~1â€“2 req/s).
- Respect BLAST, Liquipedia, and sheet owners' Terms of Service.
- Not affiliated with Psyonix, BLAST, or Liquipedia.

## License

MIT Â© 2026 ark-daemon â€” see [LICENSE](LICENSE).
## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security reports: [SECURITY.md](SECURITY.md). Changes: [CHANGELOG.md](CHANGELOG.md).
