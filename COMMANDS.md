# `rl-scraper`

Async Rocket League esports scraper (<span style="font-weight: bold">BLAST</span>, <span style="font-weight: bold">Liquipedia</span>, CSV sheets).

**Usage**:

```console
$ rl-scraper [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `export`: Export SQLite tables to Parquet files.
* `status`: Show row counts for the scraper database.
* `scrape`: Run one or more configured extraction jobs.

## `rl-scraper export`

Export SQLite tables to Parquet files.

**Usage**:

```console
$ rl-scraper export [OPTIONS]
```

**Options**:

* `-o, --output-dir PATH`: Parquet output directory.
* `--help`: Show this message and exit.

## `rl-scraper status`

Show row counts for the scraper database.

**Usage**:

```console
$ rl-scraper status [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

## `rl-scraper scrape`

Run one or more configured extraction jobs.

**Usage**:

```console
$ rl-scraper scrape [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `blast`: Scrape BLAST.tv / BLAST API Rocket League...
* `liquipedia`: Scrape Liquipedia Rocket League wiki pages.
* `drekt`: Scrape optional community CSV sheets...
* `all`: Run BLAST, Liquipedia, then Drekt...

### `rl-scraper scrape blast`

Scrape BLAST.tv / BLAST API Rocket League data.

**Usage**:

```console
$ rl-scraper scrape blast [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `rl-scraper scrape liquipedia`

Scrape Liquipedia Rocket League wiki pages.

**Usage**:

```console
$ rl-scraper scrape liquipedia [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `rl-scraper scrape drekt`

Scrape optional community CSV sheets (no-op if URLs unset).

**Usage**:

```console
$ rl-scraper scrape drekt [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `rl-scraper scrape all`

Run BLAST, Liquipedia, then Drekt sequentially.

**Usage**:

```console
$ rl-scraper scrape all [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.
