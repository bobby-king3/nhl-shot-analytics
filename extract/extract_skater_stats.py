import logging
from datetime import datetime, timezone
from extract.connection import get_connection
from extract.logging_config import setup_logging
from extract.nhl_client.nhl_api import get_stats

logger = logging.getLogger(__name__)


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
            logger.info("Season %d: skipped (%d skaters cached)", season_id, existing)
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
        """
        INSERT INTO raw_player_stats (
            player_id, season_id, team_abbrev, position,
            games_played, goals, assists, points, plus_minus,
            pp_goals, pp_points, sh_goals, sh_points,
            shots, shooting_pct, toi_per_game, ingested_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        rows,
    )
    return len(rows)


def main():
    con = get_connection()
    create_table(con)

    seasons = get_seasons(con)
    logger.info("Seasons to process: %s", seasons)

    for season in seasons:
        count = extract_season(con, season)
        if count is not None:
            logger.info("Season %d: %d skaters loaded", season, count)

    con.close()
    logger.info("Skater stats extraction complete.")


if __name__ == "__main__":
    setup_logging()
    main()
