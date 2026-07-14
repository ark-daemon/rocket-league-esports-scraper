# Rocket League Esports Scraper

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-beta-orange.svg)](CHANGELOG.md)

> Async multi-source pipeline for Rocket League esports -- BLAST.tv HTTP/JSON (primary), Liquipedia HTML, optional Google Sheets CSV -- SQLite staging, Parquet export, and fleet match snapshots.

**Fleet:** [vlr-scraper](https://github.com/ark-daemon/vlr-scraper) · [hltv-scraper](https://github.com/ark-daemon/hltv-scraper) · [dota2-scraper](https://github.com/ark-daemon/dota2-scraper) · [lol-esports-scraper](https://github.com/ark-daemon/lol-esports-scraper)

## Features

- **BLAST.tv API path** -- httpx JSON for matches and tournament discovery (happy path)
- **Liquipedia structure** -- tournaments, rosters, transfers, earnings-shaped rows
- **Optional Drekt sheets** -- CSV URLs when configured; clean skip when empty
- **Game-level stats** -- player game stats; boost/positioning when payloads include them
- **Parquet table export** -- pandas + pyarrow
- **Fleet snapshot** -- match-grain `export/` (`data.json` + `csv` + `parquet` + `manifest.json`)
- **Optional R2 publish** -- overwrite-in-place upload with public manifest verification

Maturity: **beta (`0.1.0`)**. Deep advanced stats probing is **off by default**. Not affiliated with Psyonix, BLAST, or Liquipedia.

## Getting started

```bash
git clone https://github.com/ark-daemon/rocket-league-scraper.git
cd rocket-league-scraper

python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate

pip install -e ".[dev]"
cp .env.example .env   # optional -- public defaults work for many paths

rl-scraper --help
```

CloakBrowser is only needed if you enable deep-stat HTML probes or hit that code path.

## Usage

```bash
rl-scraper scrape liquipedia
rl-scraper scrape blast
rl-scraper scrape drekt          # no-ops unless RL_DREKT_CSV_URLS set
rl-scraper scrape all
rl-scraper status
rl-scraper export -o exports

# Fleet match snapshot (export/)
rl-scraper snapshot
rl-scraper snapshot --publish
rl-scraper publish
```

Full Typer-generated CLI docs: [COMMANDS.md](COMMANDS.md).

## Architecture

```
rl-scraper scrape {blast|liquipedia|drekt|all}
        |
        +-- BlastFetcher
        |     httpx -> api.blast.tv JSON
        |     optional CloakBrowser if probe_deep_stats needs HTML
        |     QueuePipeline workers -> Storage upserts
        |
        +-- LiquipediaFetcher
        |     httpx -> liquipedia.net/rocketleague
        |     selectolax/BS parsers
        |
        +-- DrektFetcher
              httpx -> CSV export URLs (if RL_DREKT_CSV_URLS non-empty)
              else: no-op run status "skipped"
        |
        v
  SQLite (embedded SCHEMA) + scrape_runs
        |
        +--> export_parquet -> exports/*.parquet
        +--> snapshot       -> export/
```

**Resilience:**

- RateLimiter / per-source delay (`RL_*_RATE_LIMIT_SECONDS`)
- tenacity / manual retry loops on some HTTP calls -- **not** a global circuit breaker
- CloakBrowser for rendered BLAST pages in helper paths; default scrape is **API/httpx-first**

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
| `RL_MAX_CONCURRENCY` | `6` | Pipeline worker ceiling (BLAST caps at min(...,4)) |
| `RL_BLAST_FINGERPRINT_SEED` | `42069` | CloakBrowser fingerprint if used |
| `RL_BLAST_PROBE_DEEP_STATS` | `false` | Extra stats endpoint probing |
| `RL_BLAST_MAX_DISCOVERED_TOURNAMENTS` | `16` | Cap on auto-discovered RLCS slugs |
| `RL_USER_AGENT` | research bot string | HTTP UA |
| `RL_BLAST_TOURNAMENT_SLUGS` | `rlcs-world-championship-2026` | Seed slugs (+ discovery merge) |
| `RL_LIQUIPEDIA_SEED_PAGES` | RLCS 2026/2025 + Transfers | Wiki seeds |
| `RL_RLCS_REGIONS` | NA,EU,SAM,OCE,MENA,APAC,SSA | Region tags |

**R2 publish** (optional):

| Variable | Role |
|----------|------|
| `R2_ACCOUNT_ID` | Cloudflare account id |
| `R2_ACCESS_KEY_ID` | R2 API token access key |
| `R2_SECRET_ACCESS_KEY` | R2 API token secret |
| `R2_BUCKET` | Bucket name |
| `R2_PUBLIC_BASE_URL` | Public base, no trailing slash |

Objects land at `{base}/rl/{data.json,data.csv,data.parquet,manifest.json}`.

## Data model

Tables (`storage.SCHEMA` + optional `drekt_stats`):

`tournaments`, `teams`, `players`, `matches`, `games`, `player_game_stats`, `boost_stats`, `positioning_stats`, `rosters`, `staff`, `earnings`, `scrape_runs`.

Sample BLAST rows:

```json
{"id": 1, "source": "blast", "name": "RLCS Kick-Off Tournament 2026", "region": "NA"}
{"source": "blast", "team_a_name": "Vitality", "team_b_name": "Spacestation",
 "team_a_score": 1, "team_b_score": 3,
 "tournament_name": "RLCS Kick-Off Tournament 2026", "region": "NA"}
```

CLI `export` writes **Parquet only** for warehouse tables.

### Fleet snapshot (`export/`)

Match/series grain, `schema_version` **1.0**. Id strategy: `rl:{source}:{source_id}`.

`match_id`, `match_date`, `team_a`, `team_b`, `winner`, `source_url`, `status`, `score_a`, `score_b`, `event_name`, `format`, `raw_status`

> [!NOTE]
> Snapshot `export/` is separate from table Parquet dumps (`export` command / `RL_EXPORT_DIR`).

## Limitations

> [!WARNING]
> BLAST JSON contracts change without notice. Discovery regexes and parsers will lag.

- `RL_BLAST_PROBE_DEEP_STATS=false` by default -- advanced/boost/positioning coverage depends on match payloads
- Drekt is optional; empty `RL_DREKT_CSV_URLS` skips cleanly
- No circuit breaker (unlike vlr-scraper); only delays and local retries
- Entity reconciliation across sources is lightweight; expect duplicate logical teams across `source` values
- Tests cover smoke settings and Liquipedia parser fixtures -- not live BLAST integration

## Tech stack

| Layer | Used |
|-------|------|
| Runtime | Python >=3.11, asyncio |
| CLI | typer + rich (`rl-scraper`) |
| Config | pydantic + pydantic-settings |
| HTTP | httpx |
| Browser | cloakbrowser (optional deep/render paths) |
| HTML | beautifulsoup4 + selectolax |
| Retry | tenacity (and manual loops) |
| Storage | aiosqlite |
| Export | pandas + pyarrow -> Parquet; snapshot also JSON/CSV |
| Logging | loguru; tqdm / rich CLI chrome |
| Packaging | hatchling |
| Publish | boto3 optional at runtime (`pip install boto3`) |
| Quality | pytest (dev) |
