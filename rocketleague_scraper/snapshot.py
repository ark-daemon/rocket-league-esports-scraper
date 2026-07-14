"""Fleet match-level snapshot export for rocketleague-scraper."""

from __future__ import annotations

import csv
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from loguru import logger

REPO_SLUG = "rl"
GAME = "Rocket League"
SCHEMA_VERSION = "1.0"

COLUMNS = [
    "match_id",
    "match_date",
    "team_a",
    "team_b",
    "winner",
    "source_url",
    "status",
    "score_a",
    "score_b",
    "event_name",
    "format",
    "raw_status",
]

_stats = {
    "status_mapped": 0,
    "status_heuristic": 0,
    "status_anomaly_dual_true": 0,
    "date_status_anomaly": 0,
    "dropped_no_teams": 0,
    "dropped_missing_source_id": 0,
    "rows_out": 0,
}


def _reset_stats() -> None:
    for k in _stats:
        _stats[k] = 0


def _status_from_flags(
    is_live: int | None,
    is_completed: int | None,
    score_a: int | None,
    score_b: int | None,
) -> tuple[str, str | None]:
    """Returns (normalized_status, raw_status_debug)."""
    live = bool(is_live) if is_live is not None else None
    done = bool(is_completed) if is_completed is not None else None
    raw = f"is_live={is_live};is_completed={is_completed}"

    if live is True and done is True:
        _stats["status_anomaly_dual_true"] += 1
        logger.warning("RL status anomaly: is_live and is_completed both true; using A1 heuristic")
        _stats["status_heuristic"] += 1
        if score_a is not None or score_b is not None:
            return "completed", raw
        return "scheduled", raw

    if done is True:
        _stats["status_mapped"] += 1
        return "completed", raw
    if live is True:
        _stats["status_mapped"] += 1
        return "live", raw
    if done is False and live is False:
        _stats["status_mapped"] += 1
        # explicitly not live and not completed -> scheduled
        return "scheduled", raw

    # Both null / incomplete flags
    _stats["status_heuristic"] += 1
    if score_a is not None or score_b is not None:
        return "completed", raw
    return "scheduled", raw


def _parse_date(scheduled_at: str | None, *, status: str, has_scores: bool) -> str | None:
    """RL scheduled_at is ISO-8601 from BLAST (UTC)."""
    if not scheduled_at:
        return None
    next_year = datetime.now(UTC).year + 1
    try:
        parsed = datetime.fromisoformat(str(scheduled_at).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
    except ValueError:
        return None
    if parsed.year < 2015 or parsed.year > next_year:
        logger.warning("RL date out of bounds: {}", parsed.isoformat())
        return None
    # scheduled_at is schedule field; if status completed with scores, ok
    if status == "scheduled" and has_scores:
        _stats["date_status_anomaly"] += 1
        logger.warning("RL date/status anomaly: scheduled status but scores present")
    return parsed.date().isoformat()


def build_rows(db_path: str | Path) -> list[dict[str, Any]]:
    _reset_stats()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """
        SELECT id, source, source_id, scheduled_at, team_a_name, team_b_name,
               team_a_score, team_b_score, winner_name, is_live, is_completed,
               tournament_name, series_format
        FROM matches
        """
    )
    rows_out: list[dict[str, Any]] = []
    for r in cur:
        team_a = (r["team_a_name"] or "").strip() or None
        team_b = (r["team_b_name"] or "").strip() or None
        if not team_a and not team_b:
            _stats["dropped_no_teams"] += 1
            continue

        source = (r["source"] or "").strip()
        source_id = (r["source_id"] or "").strip()
        if not source or not source_id:
            _stats["dropped_missing_source_id"] += 1
            logger.warning("RL row id={} missing source/source_id; dropped", r["id"])
            continue

        score_a = int(r["team_a_score"]) if r["team_a_score"] is not None else None
        score_b = int(r["team_b_score"]) if r["team_b_score"] is not None else None
        status, raw_status = _status_from_flags(r["is_live"], r["is_completed"], score_a, score_b)
        has_scores = score_a is not None or score_b is not None
        match_date = _parse_date(r["scheduled_at"], status=status, has_scores=has_scores)

        winner = (r["winner_name"] or "").strip() or None
        if winner is not None and winner not in (team_a, team_b):
            winner = None

        # No safe public match URL without path research; leave null.
        source_url = None

        rows_out.append(
            {
                "match_id": f"{REPO_SLUG}:{source}:{source_id}",
                "match_date": match_date,
                "team_a": team_a,
                "team_b": team_b,
                "winner": winner,
                "source_url": source_url,
                "status": status,
                "score_a": score_a,
                "score_b": score_b,
                "event_name": r["tournament_name"],
                "format": r["series_format"],
                "raw_status": raw_status,
            }
        )
    conn.close()
    _stats["rows_out"] = len(rows_out)
    return rows_out


def write_snapshot(db_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = build_rows(db_path)
    if not rows:
        logger.warning("snapshot empty after filters")

    (out / "data.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out / "data.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in COLUMNS})
    try:
        import pandas as pd

        pd.DataFrame(rows, columns=COLUMNS).to_parquet(out / "data.parquet", index=False)
    except Exception as exc:
        logger.error("parquet failed: {}", exc)

    manifest = {
        "source": REPO_SLUG,
        "game": GAME,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "record_count": len(rows),
        "schema_version": SCHEMA_VERSION,
        "columns": COLUMNS,
        "files": {"json": "data.json", "csv": "data.csv", "parquet": "data.parquet"},
        "stats": dict(_stats),
        "id_strategy": "rl:{source}:{source_id}",
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(
        "snapshot {} rows mapped={} heuristic={} dual_true={}",
        len(rows),
        _stats["status_mapped"],
        _stats["status_heuristic"],
        _stats["status_anomaly_dual_true"],
    )
    return manifest
