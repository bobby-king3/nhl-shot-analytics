"""Load the current-season MoneyPuck shot CSV before dbt runs."""

import hashlib
import io
import logging
import os
import re
import tempfile
import zipfile
from datetime import datetime, timezone

import duckdb
import httpx

from extract.connection import get_connection
from extract.logging_config import setup_logging

logger = logging.getLogger(__name__)

# Update the repository variable when a new season's ZIP appears on the data page.
DEFAULT_URL = "https://peter-tanner.com/moneypuck/downloads/shots_2025.zip"
URL_PATTERN = r"https://peter-tanner\.com/moneypuck/downloads/shots_(\d{4})\.zip"
SHOT_COLUMNS = (
    "game_id", "shotID", "shooterPlayerId", "shooterName", "period", "time",
    "xCordAdjusted", "yCordAdjusted", "shotType", "event", "xGoal",
    "shotRush", "shotRebound", "isPlayoffGame", "season", "team",
)


def refresh(con, url):
    match = re.fullmatch(URL_PATTERN, url)
    if not match:
        raise ValueError("MONEYPUCK_SHOTS_URL must be a shots_YYYY.zip download URL")
    season = int(match.group(1))

    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_moneypuck_shots (
            game_id BIGINT, shotID BIGINT, shooterPlayerId DOUBLE,
            shooterName VARCHAR, period BIGINT, time BIGINT,
            xCordAdjusted BIGINT, yCordAdjusted BIGINT, shotType VARCHAR,
            event VARCHAR, xGoal DOUBLE, shotRush BIGINT,
            shotRebound BIGINT, isPlayoffGame BIGINT, season BIGINT, team VARCHAR
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_moneypuck_imports (
            season INTEGER PRIMARY KEY, source_url VARCHAR, etag VARCHAR,
            last_modified VARCHAR, sha256 VARCHAR, row_count BIGINT,
            ingested_at TIMESTAMP
        )
    """)

    try:
        latest_season = con.execute("""
            SELECT max(CAST(left(CAST(game_id AS VARCHAR), 4) AS INTEGER))
            FROM raw_play_by_play
            WHERE substr(CAST(game_id AS VARCHAR), 5, 2) IN ('02', '03')
        """).fetchone()[0]
    except duckdb.CatalogException:
        latest_season = None 
    if latest_season and latest_season > season:
        raise ValueError(
            f"NHL shots include {latest_season}, but MoneyPuck URL is for {season}; "
            "update MONEYPUCK_SHOTS_URL after the new ZIP is published"
        )

    previous = con.execute("""
        SELECT etag, last_modified, sha256 FROM raw_moneypuck_imports WHERE season = ?
    """, [season]).fetchone()
    headers = {}
    if previous:
        if previous[0]:
            headers["If-None-Match"] = previous[0]
        if previous[1]:
            headers["If-Modified-Since"] = previous[1]

    response = httpx.get(url, headers=headers, timeout=120, follow_redirects=True)
    if response.status_code == 304:
        logger.info("MoneyPuck %d: unchanged", season)
        return 0
    response.raise_for_status()
    etag, modified = response.headers.get("ETag"), response.headers.get("Last-Modified")
    digest = hashlib.sha256(response.content).hexdigest()
    if previous and digest == previous[2]:
        con.execute("""
            UPDATE raw_moneypuck_imports
            SET source_url = ?, etag = ?, last_modified = ? WHERE season = ?
        """, [url, etag, modified, season])
        logger.info("MoneyPuck %d: unchanged", season)
        return 0

    expected_csv = f"shots_{season}.csv"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        if archive.namelist() != [expected_csv]:
            raise ValueError(f"Expected one {expected_csv} file in MoneyPuck ZIP")
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = archive.extract(expected_csv, temp_dir)
            con.execute("DROP TABLE IF EXISTS mp_shots_stage")
            con.execute(f"""
                CREATE TEMP TABLE mp_shots_stage AS
                SELECT {', '.join(SHOT_COLUMNS)} FROM read_csv_auto(?)
            """, [csv_path])

    count, invalid = con.execute("""
        SELECT count(*), count(*) FILTER (
            WHERE season != ? OR season IS NULL
               OR game_id IS NULL OR shotID IS NULL OR xGoal IS NULL
        ) FROM mp_shots_stage
    """, [season]).fetchone()
    existing = con.execute(
        "SELECT count(*) FROM raw_moneypuck_shots WHERE season = ?", [season]
    ).fetchone()[0]
    if not count or invalid or (existing >= 100 and count < existing * 0.9):
        raise ValueError(
            f"MoneyPuck {season} CSV looks incomplete: {count} rows, "
            f"{invalid} invalid rows, {existing} previously stored"
        )

    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM raw_moneypuck_shots WHERE season = ?", [season])
        con.execute(f"""
            INSERT INTO raw_moneypuck_shots ({', '.join(SHOT_COLUMNS)})
            SELECT {', '.join(SHOT_COLUMNS)} FROM mp_shots_stage
        """)
        con.execute("DELETE FROM raw_moneypuck_imports WHERE season = ?", [season])
        con.execute("""
            INSERT INTO raw_moneypuck_imports VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [season, url, etag, modified, digest, count, datetime.now(timezone.utc)])
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    logger.info("MoneyPuck %d: loaded %d shots", season, count)
    return count


def main():
    con = get_connection()
    try:
        refresh(con, os.environ.get("MONEYPUCK_SHOTS_URL", DEFAULT_URL))
    finally:
        con.close()


if __name__ == "__main__":
    setup_logging()
    main()
