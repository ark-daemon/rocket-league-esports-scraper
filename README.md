# Rocket League Esports Scraper

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](CHANGELOG.md)

Async multi-source pipeline for **Rocket League esports** - BLAST.tv HTTP/JSON (primary), Liquipedia HTML, optional Google Sheets CSV - SQLite staging and Parquet export.

**Fleet:** [vlr-scraper](https://github.com/ark-daemon/vlr-scraper) | [hltv-scraper](https://github.com/ark-daemon/hltv-scraper) | [dota2-scraper](https://github.com/ark-daemon/dota2-scraper) | [lol-esports-scraper](https://github.com/ark-daemon/lol-esports-scraper)

---

## What it does

Builds a local warehouse of RLCS-oriented entities: tournaments, teams, players, series/matches, games, player game stats (plus optional boost/positioning tables), rosters, staff, and earnings. BLAST is the live competitive feed path; Liquipedia supplies structure/rosters/transfers; Drekt-style sheets are optional and skipped when unconfigured.

Maturity: **beta (`0.1.0`)**. API and wiki shapes change; deep advanced stats probing is **off by default**. Not affiliated with Psyonix, BLAST, or Liquipedia.

---

## Architecture

```
rl-scraper scrape {blast|liquipedia|drekt|all}
        |
        +-- BlastFetcher
        |     httpx -> api.blast.tv JSON (matches list, match payloads)
        |     optional CloakBrowser only if probe_deep_stats paths need HTML
        |     QueuePipeline workers -> Storage upserts
        |
        +-- LiquipediaFetcher
        |     httpx -> liquipedia.net/rocketleague pages
        |     selectolax/BS parsers (tournaments, rosters, earnings, ...)
        |
        +-- DrektFetcher
              httpx -> CSV export URLs (if RL_DREKT_CSV_URLS non-empty)
              else: no-op run status "skipped"
        |
        v
  SQLite (embedded SCHEMA in storage.py) + scrape_runs
        |
        v
  export_parquet -> exports/*.parquet
```

**Resilience vocabulary:**

- **RateLimiter / per-source delay** on HTTP clients (`RL_*_RATE_LIMIT_SECONDS`).
- **tenacity** / manual retry loops on some HTTP calls - **not** a global circuit breaker.
- **CloakBrowser** is a dependency and used for rendered BLAST pages in helper paths; default scrape is **API/httpx-first**.

---

## Quickstart

```bash
git clone https://github.com/ark-daemon/rocket-league-scraper.git
cd rocket-league-scraper

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -e ".[dev]"
# CloakBrowser only needed if you enable deep-stat HTML probes or hit that code path.

cp .env.example .env   # optional - code has working public defaults

rl-scraper --help
rl-scraper scrape liquipedia
rl-scraper scrape blast
rl-scraper scrape drekt          # no-ops unless RL_DREKT_CSV_URLS set
rl-scraper scrape all
rl-scraper status
rl-scraper export -o exports
```

---

## Configuration

`pydantic-settings` with prefix **`RL_`** (`rocketleague_scraper/config.py`). Empty CSV-like env values are supported via `NoDecode` + split validators.

| Variable | Default | Role |
|----------|---------|------|
| `RL_DB_PATH` | `rocketleague.db` | SQLite |
| `RL_EXPORT_DIR` | `exports` | Parquet dir |
| `RL_LOG_DIR` | `logs` | Logs |
| `RL_BLAST_BASE_URL` | `https://blast.tv/rl` | Site base (discovery HTML) |
| `RL_BLAST_API_BASE_URL` | `https://api.blast.tv` | JSON API root |
| `RL_LIQUIPEDIA_BASE_URL` | `https://liquipedia.net/rocketleague` | Wiki base |
| `RL_DREKT_CSV_URLS` | empty tuple | Comma-separated sheet CSV URLs |
| `RL_HTTP_TIMEOUT_SECONDS` | `30` | Timeout |
| `RL_BLAST_RATE_LIMIT_SECONDS` | `0.75` | BLAST spacing |
| `RL_LIQUIPEDIA_RATE_LIMIT_SECONDS` | `2.0` | Liquipedia spacing |
| `RL_SPREADSHEET_RATE_LIMIT_SECONDS` | `0.25` | Sheet spacing |
| `RL_MAX_CONCURRENCY` | `6` | Pipeline worker ceiling (BLAST caps workers at min(...,4)) |
| `RL_BLAST_FINGERPRINT_SEED` | `42069` | CloakBrowser fingerprint if used |
| `RL_BLAST_PROBE_DEEP_STATS` | `false` | Extra stats endpoint probing |
| `RL_BLAST_MAX_DISCOVERED_TOURNAMENTS` | `16` | Cap on auto-discovered RLCS slugs |
| `RL_USER_AGENT` | research bot string | HTTP UA |
| `RL_BLAST_TOURNAMENT_SLUGS` | `rlcs-world-championship-2026` | Seed slugs (+ discovery merge) |
| `RL_LIQUIPEDIA_SEED_PAGES` | RLCS 2026/2025 + Transfers | Wiki seeds |
| `RL_RLCS_REGIONS` | NA,EU,SAM,OCE,MENA,APAC,SSA | Region tags |

---

## Data model + sample output

Tables (from `storage.SCHEMA` + optional `drekt_stats` created by Drekt fetcher):

`tournaments`, `teams`, `players`, `matches`, `games`, `player_game_stats`, `boost_stats`, `positioning_stats`, `rosters`, `staff`, `earnings`, `scrape_runs`.

**Sample rows** (local BLAST scrape):

```json
// tournaments
{"id": 1, "source": "blast", "name": "RLCS Kick-Off Tournament 2026", "region": "NA", "prize_pool_total": 1.0}
{"id": 8, "source": "blast", "name": "RLCS Boston Major 1 2026", "prize_pool_total": 354000.0}

// matches
{"source": "blast", "team_a_name": "Vitality", "team_b_name": "Spacestation",
 "team_a_score": 1, "team_b_score": 3,
 "tournament_name": "RLCS Kick-Off Tournament 2026", "region": "NA"}
```

Export is **Parquet only** via `rl-scraper export`.

---

## Current limitations

- **BLAST JSON contracts change** without notice; discovery regexes and parsers will lag.
- **`RL_BLAST_PROBE_DEEP_STATS=false` by default** - advanced/boost/positioning coverage depends on what the match payload already includes.
- **Drekt is optional**; empty `RL_DREKT_CSV_URLS` skips cleanly.
- **No circuit breaker** (unlike vlr-scraper); only delays and local retries.
- **CloakBrowser** is installed but not on the happy path for default BLAST API scrapes.
- **Entity reconciliation** across sources is lightweight (`reconciliation.py`); expect duplicate logical teams across `source` values.
- **Tests** cover smoke settings and Liquipedia parser fixtures - not live BLAST integration.

---

## Tech stack

| Layer | Actually used |
|-------|----------------|
| Runtime | Python >=3.11, asyncio |
| CLI | typer, rich (`rl-scraper`) |
| Config | pydantic + pydantic-settings |
| HTTP | httpx |
| Browser | cloakbrowser (optional deep/render paths) |
| HTML | beautifulsoup4 + selectolax |
| Retry | tenacity (and manual loops) |
| Storage | aiosqlite |
| Export | pandas + pyarrow -> Parquet |
| Logging | loguru; tqdm for progress / rich CLI chrome |
| Packaging | hatchling |
| Quality | pytest (dev) |

---

## License

MIT (c) ark-daemon - see [LICENSE](LICENSE).

See also [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md).

## Command reference

Full Typer-generated CLI docs: [COMMANDS.md](COMMANDS.md).
