"""Typer CLI for the Rocket League scraper."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from .cli_ui import (
    configure_rich_logging,
    console,
    end_summary_table,
    scrape_progress,
    startup_panel,
    status_table,
    timed_run,
)
from .config import Settings, get_settings
from .fetchers.blast_fetcher import BlastFetcher
from .fetchers.drekt_fetcher import DrektFetcher
from .fetchers.liquipedia_fetcher import LiquipediaFetcher
from .storage import Storage

app = typer.Typer(
    name="rl-scraper",
    help="Async Rocket League esports scraper ([bold]BLAST[/], [bold]Liquipedia[/], CSV sheets).",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_show_locals=False,
)
scrape_app = typer.Typer(
    help="Run one or more configured extraction jobs.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)
app.add_typer(scrape_app, name="scrape")


def bootstrap() -> tuple[Settings, Storage]:
    settings = get_settings()
    configure_rich_logging("INFO", settings.log_dir / "rocketleague_scraper.log")
    return settings, Storage(settings.db_path)


def _boot(settings: Settings, target: str) -> None:
    startup_panel(
        title="rl-scraper · run config",
        rows={
            "Target": target,
            "DB path": settings.db_path,
            "Export dir": settings.export_dir,
            "Max concurrency": settings.max_concurrency,
            "BLAST rate (s)": settings.blast_rate_limit_seconds,
            "Liquipedia rate (s)": settings.liquipedia_rate_limit_seconds,
            "Output format": "parquet (on export)",
            "User-Agent": settings.user_agent[:56] + ("…" if len(settings.user_agent) > 56 else ""),
        },
    )


async def run_source(source: str) -> tuple[int, int]:
    settings, storage = bootstrap()
    await storage.init()
    if source == "blast":
        return await BlastFetcher(settings, storage).scrape()
    if source == "liquipedia":
        return await LiquipediaFetcher(settings, storage).scrape()
    if source == "drekt":
        return await DrektFetcher(settings, storage).scrape()
    raise typer.BadParameter(f"Unknown source: {source}")


def _scrape_one(source: str) -> None:
    settings = get_settings()
    _boot(settings, source)
    with timed_run() as elapsed, scrape_progress() as progress:
        task = progress.add_task(f"scrape {source}", total=None)
        seen, written = asyncio.run(run_source(source))
        progress.update(task, description=f"scrape {source} · done")
    end_summary_table(
        title="Scrape summary",
        rows=[
            ("Source", source),
            ("Items seen", f"{seen:,}"),
            ("Rows written", f"{written:,}"),
            ("Errors/skips", "see logs"),
        ],
        duration_s=elapsed[0],
    )


@scrape_app.command("blast")
def scrape_blast() -> None:
    """Scrape BLAST.tv / BLAST API Rocket League data."""
    _scrape_one("blast")


@scrape_app.command("liquipedia")
def scrape_liquipedia() -> None:
    """Scrape Liquipedia Rocket League wiki pages."""
    _scrape_one("liquipedia")


@scrape_app.command("drekt")
def scrape_drekt() -> None:
    """Scrape optional community CSV sheets (no-op if URLs unset)."""
    _scrape_one("drekt")


@scrape_app.command("all")
def scrape_all() -> None:
    """Run BLAST, Liquipedia, then Drekt sequentially."""
    settings = get_settings()
    _boot(settings, "blast + liquipedia + drekt")
    results: list[tuple[str, int, int]] = []
    with timed_run() as elapsed, scrape_progress() as progress:
        task = progress.add_task("scrape all", total=3)
        for source in ("blast", "liquipedia", "drekt"):
            progress.update(task, description=f"scrape {source}")
            seen, written = asyncio.run(run_source(source))
            results.append((source, seen, written))
            progress.advance(task)
    end_summary_table(
        title="Scrape summary",
        rows=[
            (src, f"seen={seen:,} written={written:,}")
            for src, seen, written in results
        ],
        duration_s=elapsed[0],
    )


@app.command("export")
def export(
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Parquet output directory."),
    ] = None,
) -> None:
    """Export SQLite tables to Parquet files."""

    async def _run() -> list[Path]:
        settings, storage = bootstrap()
        await storage.init()
        return await storage.export_parquet(output_dir or settings.export_dir)

    settings = get_settings()
    configure_rich_logging("INFO", settings.log_dir / "rocketleague_scraper.log")
    target = output_dir or settings.export_dir
    startup_panel(
        title="rl-scraper · export",
        rows={"DB path": settings.db_path, "Output format": "parquet", "Export dir": target},
    )
    with timed_run() as elapsed:
        paths = asyncio.run(_run())
    end_summary_table(
        title="Export summary",
        rows=[("Tables", len(paths))],
        outputs=paths,
        duration_s=elapsed[0],
    )


@app.command("status")
def status() -> None:
    """Show row counts for the scraper database."""

    async def _run() -> dict[str, int]:
        _, storage = bootstrap()
        await storage.init()
        return await storage.counts()

    counts = asyncio.run(_run())
    status_table("Extraction pipeline status", counts)


@app.command("snapshot")
def snapshot(
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Directory for data.json/csv/parquet + manifest.json."),
    ] = Path("export"),
    publish: Annotated[
        bool,
        typer.Option("--publish", help="Upload export/ to Cloudflare R2 after writing."),
    ] = False,
) -> None:
    """Write fleet match-level snapshot for dashboard / R2 publish."""
    from .snapshot import write_snapshot

    settings = get_settings()
    configure_rich_logging("INFO", settings.log_dir / "rocketleague_scraper.log")
    startup_panel(
        title="rl-scraper · snapshot",
        rows={
            "DB path": settings.db_path,
            "Output dir": out,
            "Grain": "match/series",
            "ID strategy": "rl:{source}:{source_id}",
            "Publish R2": publish,
        },
    )
    with timed_run() as elapsed:
        manifest = write_snapshot(settings.db_path, out)
    end_summary_table(
        title="Snapshot summary",
        rows=[
            ("Records", manifest.get("record_count")),
            ("Status mapped", manifest.get("stats", {}).get("status_mapped")),
            ("Status heuristic", manifest.get("stats", {}).get("status_heuristic")),
            ("Dual-true anomalies", manifest.get("stats", {}).get("status_anomaly_dual_true")),
        ],
        outputs=[out / "manifest.json", out / "data.json", out / "data.csv", out / "data.parquet"],
        duration_s=elapsed[0],
    )
    if publish:
        _publish_r2(out, "rl")


@app.command("publish")
def publish_cmd(
    out: Annotated[Path, typer.Option("--out", "-o", help="Local export directory.")] = Path(
        "export"
    ),
) -> None:
    """Upload export/ snapshot to Cloudflare R2 and verify public manifest."""
    settings = get_settings()
    configure_rich_logging("INFO", settings.log_dir / "rocketleague_scraper.log")
    _publish_r2(out, "rl")


def _publish_r2(out: Path, slug: str) -> None:
    from .r2_publish import upload_snapshot

    with timed_run() as elapsed:
        result = upload_snapshot(export_dir=out, repo_slug=slug)
    end_summary_table(
        title="Publish summary",
        rows=[("Records verified", result["record_count"]), ("Manifest URL", result["manifest_url"])],
        outputs=list(result["urls"].values()),
        duration_s=elapsed[0],
    )
    console.print(f"[bold green]Public manifest:[/] {result['manifest_url']}")


if __name__ == "__main__":
    app()
