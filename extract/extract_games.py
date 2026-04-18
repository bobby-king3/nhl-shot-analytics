import sys
sys.path.append(".")

import duckdb
from datetime import date, timedelta
from extract.nhl_client.nhl_api import get

DB_PATH = "data/nhl.duckdb"
SEASON_START_DATES = [date(2023, 10, 10), date(2024, 10, 8), date(2025, 10, 7)]


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


def fetch_all_games(con):
    existing = get_existing_game_ids(con)
    rows = []
    end = date.today()

    for start in SEASON_START_DATES:
        current = start
        while current <= end:
            data = get(f"/schedule/{current}")
            for week in data.get("gameWeek", []):
                for game in week.get("games", []):
                    gid = game.get("id")
                    if not gid or gid in existing:
                        continue
                    if game.get("gameState") != "OFF":
                        continue

                    home = game.get("homeTeam", {})
                    away = game.get("awayTeam", {})
                    outcome = game.get("gameOutcome", {})

                    start_time = game.get("startTimeUTC")
                    game_date = start_time[:10] if start_time else None

                    rows.append((
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
                        date.today().isoformat(),
                    ))
            current += timedelta(weeks=1)

    if rows:
        con.executemany("INSERT OR IGNORE INTO raw_games VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        print(f"Inserted {len(rows)} games.")
    else:
        print("No new games to insert.")


def main():
    con = duckdb.connect(DB_PATH)
    create_table(con)
    fetch_all_games(con)
    con.close()
    print("Done.")


if __name__ == "__main__":
    main()
