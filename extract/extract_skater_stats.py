import sys
sys.path.append(".")

from datetime import datetime, timezone
from extract.connection import get_connection
from extract.nhl_client.nhl_api import get_stats


def create_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_player_stats (
            player_id       INTEGER,
            season_id       INTEGER,
            team_abbrev     VARCHAR,
            position        VARCHAR,
            games_played    INTEGER,
            goals           INTEGER,
            assists         INTEGER,
            points          INTEGER,
            plus_minus      INTEGER,
            pp_goals        INTEGER,
            pp_points       INTEGER,
            sh_goals        INTEGER,
            sh_points       INTEGER,
            shots           INTEGER,
            shooting_pct    DOUBLE,
            toi_per_game    DOUBLE,
            ingested_at     TIMESTAMP,
            PRIMARY KEY (player_id, season_id)
        )
    """)


def get_seasons(con):
    rows = con.execute(
        "SELECT DISTINCT season FROM raw_play_by_play ORDER BY season"
    ).fetchall()
    return [r[0] for r in rows]


def is_season_complete(season_id):
    return (season_id % 10000) < datetime.now(timezone.utc).year


def extract_season(con, season_id):
    if is_season_complete(season_id):
        existing = con.execute(
            "SELECT COUNT(*) FROM raw_player_stats WHERE season_id = ?", [season_id]
        ).fetchone()[0]
        if existing > 0:
            print(f"Season {season_id}: skipped ({existing} skaters)")
            return None

    data = get_stats(
        f"/skater/summary?limit=-1&isAggregate=true&cayenneExp=seasonId={season_id}"
    )
    skaters = data.get("data", [])

    con.execute("DELETE FROM raw_player_stats WHERE season_id = ?", [season_id])

    rows = [
        (
            s["playerId"],
            season_id,
            s.get("teamAbbrevs", ""),
            s.get("positionCode", ""),
            s.get("gamesPlayed", 0),
            s.get("goals", 0),
            s.get("assists", 0),
            s.get("points", 0),
            s.get("plusMinus", 0),
            s.get("ppGoals", 0),
            s.get("ppPoints", 0),
            s.get("shGoals", 0),
            s.get("shPoints", 0),
            s.get("shots", 0),
            s.get("shootingPct"),
            s.get("timeOnIcePerGame"),
            datetime.now(timezone.utc),
        )
        for s in skaters
    ]

    con.executemany(
        "INSERT INTO raw_player_stats VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        rows,
    )
    return len(rows)


def main():
    con = get_connection()
    create_table(con)

    seasons = get_seasons(con)
    print(f"Seasons to process: {seasons}")

    for season in seasons:
        count = extract_season(con, season)
        if count is not None:
            print(f"Season {season}: {count} skaters loaded")

    con.close()
    print("Done.")


if __name__ == "__main__":
    main()
