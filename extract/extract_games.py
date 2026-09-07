import logging
import os
from datetime import date, datetime, timedelta, timezone

from extract.connection import get_connection
from extract.logging_config import setup_logging
from extract.nhl_client.nhl_api import get

logger = logging.getLogger(__name__)

HISTORY_START_DATE = date(2023, 10, 10)
RECOVERY_OVERLAP_DAYS = 7

GAME_COLUMNS = (
    "season",
    "game_type",
    "game_date",
    "start_time_utc",
    "venue",
    "home_team_id",
    "home_team_abbrev",
    "home_score",
    "away_team_id",
    "away_team_abbrev",
    "away_score",
    "last_period_type",
)


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
            ingested_at       TIMESTAMP,
            updated_at        TIMESTAMP
        )
    """)
    con.execute("ALTER TABLE raw_games ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP")
    con.execute("UPDATE raw_games SET updated_at = ingested_at WHERE updated_at IS NULL")


def get_last_game_date(con):
    return con.execute("SELECT MAX(game_date) FROM raw_games").fetchone()[0]


def get_schedule_window(con, full_backfill=False, today=None):
    end = today or date.today()
    last_game_date = get_last_game_date(con)

    if full_backfill or last_game_date is None:
        return HISTORY_START_DATE, end

    start = max(HISTORY_START_DATE, last_game_date - timedelta(days=RECOVERY_OVERLAP_DAYS))
    return start, end


def get_schedule_request_dates(start, end):
    current = start
    while current <= end:
        yield current
        current += timedelta(weeks=1)


def parse_start_time(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def game_to_row(game, schedule_date, observed_at):
    gid = game.get("id")
    if not gid or game.get("gameState") != "OFF":
        return None

    home = game.get("homeTeam", {})
    away = game.get("awayTeam", {})
    outcome = game.get("gameOutcome", {})
    start_time = parse_start_time(game.get("startTimeUTC"))
    game_date = date.fromisoformat(schedule_date)

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
        observed_at,
        observed_at,
    )


def fetch_schedule_rows(start, end):
    games_by_id = {}
    request_count = 0
    observed_at = datetime.now(timezone.utc).replace(tzinfo=None)

    for request_date in get_schedule_request_dates(start, end):
        request_count += 1
        data = get(f"/schedule/{request_date}")
        for week in data.get("gameWeek", []):
            schedule_date = week.get("date")
            if not schedule_date:
                logger.warning("Skipping schedule bucket without a date for request %s.", request_date)
                continue
            for game in week.get("games", []):
                row = game_to_row(game, schedule_date, observed_at)
                if row:
                    games_by_id[row[0]] = row

    return list(games_by_id.values()), request_count


def get_existing_games(con, game_ids):
    if not game_ids:
        return {}

    placeholders = ", ".join("?" for _ in game_ids)
    columns = ", ".join(("game_id", *GAME_COLUMNS))
    rows = con.execute(
        f"SELECT {columns} FROM raw_games WHERE game_id IN ({placeholders})",
        list(game_ids),
    ).fetchall()
    return {row[0]: row[1:] for row in rows}


def upsert_games(con, rows):
    if not rows:
        return 0, 0, 0

    existing = get_existing_games(con, {row[0] for row in rows})
    changed_rows = []
    inserted = 0
    updated = 0
    unchanged = 0

    for row in rows:
        stored_values = existing.get(row[0])
        incoming_values = row[1:13]
        if stored_values is None:
            inserted += 1
            changed_rows.append(row)
        elif stored_values != incoming_values:
            updated += 1
            changed_rows.append(row)
        else:
            unchanged += 1

    if changed_rows:
        con.executemany("""
            INSERT INTO raw_games (
                game_id, season, game_type, game_date, start_time_utc, venue,
                home_team_id, home_team_abbrev, home_score,
                away_team_id, away_team_abbrev, away_score,
                last_period_type, ingested_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
                updated_at = EXCLUDED.updated_at
        """, changed_rows)

    return inserted, updated, unchanged


def fetch_all_games(con, full_backfill=False, today=None):
    start, end = get_schedule_window(con, full_backfill=full_backfill, today=today)
    mode = "full backfill" if full_backfill or start == HISTORY_START_DATE else "incremental"
    logger.info("Schedule extraction mode: %s (%s to %s).", mode, start, end)

    rows, request_count = fetch_schedule_rows(start, end)
    inserted, updated, unchanged = upsert_games(con, rows)

    logger.info(
        "Schedule requests: %d. Completed games found: %d. "
        "Games inserted: %d. Games corrected: %d. Games unchanged: %d.",
        request_count,
        len(rows),
        inserted,
        updated,
        unchanged,
    )
    return {
        "request_count": request_count,
        "games_found": len(rows),
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
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
