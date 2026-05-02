from datetime import date, datetime, timedelta, timezone
from extract.connection import get_connection
from extract.nhl_client.nhl_api import get

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
    seen = set(existing)
    rows = []
    end = date.today()

    for start in SEASON_START_DATES:
        current = start
        while current <= end:
            data = get(f"/schedule/{current}")
            for week in data.get("gameWeek", []):
                for game in week.get("games", []):
                    gid = game.get("id")
                    if not gid or gid in seen:
                        continue
                    seen.add(gid)
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
                        datetime.now(timezone.utc),
                    ))
            current += timedelta(weeks=1)

    if rows:
        con.executemany("""
            INSERT INTO raw_games (
                game_id, season, game_type, game_date, start_time_utc, venue,
                home_team_id, home_team_abbrev, home_score,
                away_team_id, away_team_abbrev, away_score,
                last_period_type, ingested_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)
        print(f"Inserted {len(rows)} games.")
    else:
        print("No new games to insert.")


def main():
    con = get_connection()
    create_table(con)
    fetch_all_games(con)
    con.close()
    print("Done.")


if __name__ == "__main__":
    main()
