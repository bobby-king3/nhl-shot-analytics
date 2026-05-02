import json
import logging
from datetime import date, datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

from extract.connection import get_connection
from extract.logging_config import setup_logging
from extract.nhl_client.nhl_api import get, get_play_by_play

logger = logging.getLogger(__name__)

SHOT_EVENT_TYPES = {"shot-on-goal", "goal", "missed-shot", "blocked-shot"}
LOOKBACK_DAYS = 3
MAX_WORKERS = 6


def get_completed_games():
    start = date.today() - timedelta(days=LOOKBACK_DAYS)
    end = date.today()

    game_ids = []
    current = start
    while current <= end:
        data = get(f"/schedule/{current}")
        for week in data.get("gameWeek", []):
            for game in week.get("games", []):
                if game.get("gameState") == "OFF":
                    game_ids.append((game["id"], game.get("season")))
        current += timedelta(weeks=1)

    return list({gid: season for gid, season in game_ids}.items())


def get_already_processed(con):
    return {
        row[0]
        for row in con.execute("SELECT DISTINCT game_id FROM raw_play_by_play").fetchall()
    }


def create_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_play_by_play (
            game_id               INTEGER,
            event_id              INTEGER,
            season                INTEGER,
            period                INTEGER,
            time_in_period        VARCHAR,
            event_type            VARCHAR,
            x_coord               DOUBLE,
            y_coord               DOUBLE,
            shot_type             VARCHAR,
            shooter_id            INTEGER,
            goalie_id             INTEGER,
            team_id               INTEGER,
            situation_code        VARCHAR,
            home_defending_side   VARCHAR,
            away_score            INTEGER,
            home_score            INTEGER,
            highlight_clip_url    VARCHAR,
            raw                   VARCHAR,
            ingested_at           TIMESTAMP,
            PRIMARY KEY (game_id, event_id)
        )
    """)


def fetch_game(game_id, season):
    pbp = get_play_by_play(game_id)
    rows = []

    for play in pbp.get("plays", []):
        if play.get("typeDescKey") not in SHOT_EVENT_TYPES:
            continue

        details = play.get("details", {})
        shooter_id = details.get("scoringPlayerId") or details.get("shootingPlayerId")

        rows.append((
            game_id,
            play.get("eventId"),
            season,
            play.get("periodDescriptor", {}).get("number"),
            play.get("timeInPeriod"),
            play.get("typeDescKey"),
            details.get("xCoord"),
            details.get("yCoord"),
            details.get("shotType"),
            shooter_id,
            details.get("goalieInNetId"),
            details.get("eventOwnerTeamId"),
            play.get("situationCode"),
            play.get("homeTeamDefendingSide"),
            details.get("awayScore"),
            details.get("homeScore"),
            details.get("highlightClipSharingUrl"),
            json.dumps(play),
            datetime.now(timezone.utc),
        ))

    return game_id, rows

def insert_game(con, game_id, rows):
    if not rows:
        return 0
    con.execute("BEGIN")
    try:
        con.executemany("""
            INSERT INTO raw_play_by_play (
                game_id, event_id, season, period, time_in_period,
                event_type, x_coord, y_coord, shot_type,
                shooter_id, goalie_id, team_id, situation_code,
                home_defending_side, away_score, home_score,
                highlight_clip_url, raw, ingested_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return len(rows)

def main():
    con = get_connection()
    create_table(con)

    already_processed = get_already_processed(con)
    all_game_ids = get_completed_games()
    new_game_ids = [(gid, season) for gid, season in all_game_ids if gid not in already_processed]

    logger.info("Total completed games found: %d", len(all_game_ids))
    logger.info("Already processed:           %d", len(already_processed))
    logger.info("New games to fetch:          %d", len(new_game_ids))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_game, gid, season): (gid, season)
            for gid, season in new_game_ids
        }
        for i, future in enumerate(as_completed(futures), 1):
            game_id, rows = future.result()
            shot_count = insert_game(con, game_id, rows)
            logger.info("[%d/%d] game %d: %d shot events", i, len(new_game_ids), game_id, shot_count)

    con.close()
    logger.info("Play-by-play extraction complete.")


if __name__ == "__main__":
    setup_logging()
    main()