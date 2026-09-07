import logging
import os
from datetime import date, datetime, timedelta, timezone

from extract.connection import get_connection
from extract.logging_config import setup_logging
from extract.nhl_client.nhl_api import get

logger = logging.getLogger(__name__)

HISTORY_START_DATE = date(2023, 10, 10)
DAILY_LOOKBACK_DAYS = 14


def create_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_games (
            game_id           INTEGER PRIMARY KEY,
            season            INTEGER,
            game_type         INTEGER,
            game_date         DATE,
            start_time_utc    TIMESTAMP,
            venue             VARCHAR,
            home_team_id      INTEGER,
            home_team_abbrev  VARCHAR,
            home_score        INTEGER,
            away_team_id      INTEGER,
            away_team_abbrev  VARCHAR,
            away_score        INTEGER,
            last_period_type  VARCHAR,
            ingested_at       TIMESTAMP
        )
    """)


def get_existing_game_ids(con):
    return {
        row[0]
        for row in con.execute("SELECT game_id FROM raw_games").fetchall()
    }


def get_schedule_window(full_backfill=False, today=None):
    end = today or date.today()
    start = HISTORY_START_DATE if full_backfill else end - timedelta(days=DAILY_LOOKBACK_DAYS)
    return start, end


def get_schedule_request_dates(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(weeks=1)


def game_to_row(game, ingested_at):
    gid = game.get("id")
    if not gid or game.get("gameState") != "OFF":
        return None

    home = game.get("homeTeam", {})
    away = game.get("awayTeam", {})
    outcome = game.get("gameOutcome", {})
    start_time = game.get("startTimeUTC")
    game_date = start_time[:10] if start_time else None

    return (
        gid,
        game.get("season"),
        game.get("gameType"),
        game_date,
        start_time,
        game.get("venue", {}).get("default"),
        home.get("id"),
        home.get("abbrev"),
        home.get("score"),
        away.get("id"),
        away.get("abbrev"),
        away.get("score"),
        outcome.get("lastPeriodType"),
        ingested_at,
    )


def fetch_schedule_rows(start, end):
    games_by_id = {}
    request_count = 0
    ingested_at = datetime.now(timezone.utc)

    for request_date in get_schedule_request_dates(start, end):
        request_count += 1
        data = get(f"/schedule/{request_date}")
        for week in data.get("gameWeek", []):
            for game in week.get("games", []):
                row = game_to_row(game, ingested_at)
                if row:
                    games_by_id[row[0]] = row

    return list(games_by_id.values()), request_count


def upsert_games(con, rows):
    if not rows:
        return 0, 0

    existing = get_existing_game_ids(con)
    incoming_ids = {row[0] for row in rows}
    inserted = len(incoming_ids - existing)
    updated = len(incoming_ids & existing)

    con.executemany("""
        INSERT INTO raw_games (
            game_id, season, game_type, game_date, start_time_utc, venue,
            home_team_id, home_team_abbrev, home_score,
            away_team_id, away_team_abbrev, away_score,
            last_period_type, ingested_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT (game_id) DO UPDATE SET
            season = EXCLUDED.season,
            game_type = EXCLUDED.game_type,
            game_date = EXCLUDED.game_date,
            start_time_utc = EXCLUDED.start_time_utc,
            venue = EXCLUDED.venue,
            home_team_id = EXCLUDED.home_team_id,
            home_team_abbrev = EXCLUDED.home_team_abbrev,
            home_score = EXCLUDED.home_score,
            away_team_id = EXCLUDED.away_team_id,
            away_team_abbrev = EXCLUDED.away_team_abbrev,
            away_score = EXCLUDED.away_score,
            last_period_type = EXCLUDED.last_period_type,
            ingested_at = EXCLUDED.ingested_at
    """, rows)

    return inserted, updated


def fetch_all_games(con, full_backfill=False, today=None):
    start, end = get_schedule_window(full_backfill=full_backfill, today=today)
    mode = "full backfill" if full_backfill else "daily"
    logger.info("Schedule extraction mode: %s (%s to %s).", mode, start, end)

    rows, request_count = fetch_schedule_rows(start, end)
    inserted, updated = upsert_games(con, rows)

    logger.info(
        "Schedule requests: %d. Completed games found: %d. Games inserted: %d. Games updated: %d.",
        request_count,
        len(rows),
        inserted,
        updated,
    )
    return {
        "request_count": request_count,
        "games_found": len(rows),
        "inserted": inserted,
        "updated": updated,
    }


def env_flag(name):
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def main():
    con = get_connection()
    create_table(con)
    fetch_all_games(con, full_backfill=env_flag("FULL_SCHEDULE_BACKFILL"))
    con.close()
    logger.info("Games extraction complete.")


if __name__ == "__main__":
    setup_logging()
    main()
