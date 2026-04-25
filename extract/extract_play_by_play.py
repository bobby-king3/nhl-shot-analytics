import sys
sys.path.append(".")

import json
from datetime import date, datetime, timedelta, timezone
from extract.connection import get_connection
from extract.nhl_client.nhl_api import get, get_play_by_play

SHOT_EVENT_TYPES = {"shot-on-goal", "goal", "missed-shot", "blocked-shot"}
SEASON_START_DATES = [date(2023, 10, 10), date(2024, 10, 8), date(2025, 10, 7)]
LOOKBACK_DAYS = 3


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


def extract_game(con, game_id, season):
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

    if rows:
        con.executemany("""
            INSERT INTO raw_play_by_play VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)

    return len(rows)


def main():
    con = get_connection()
    create_table(con)

    already_processed = get_already_processed(con)
    all_game_ids = get_completed_games()
    new_game_ids = [(gid, season) for gid, season in all_game_ids if gid not in already_processed]

    print(f"Total completed games found: {len(all_game_ids)}")
    print(f"Already processed:           {len(already_processed)}")
    print(f"New games to fetch:          {len(new_game_ids)}")

    for i, (game_id, season) in enumerate(new_game_ids, 1):
        shot_count = extract_game(con, game_id, season)
        print(f"  [{i}/{len(new_game_ids)}] game {game_id} (season {season}): {shot_count} shot events")

    con.close()
    print("Done.")


if __name__ == "__main__":
    main()
