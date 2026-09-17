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
            playoff_games_played INTEGER,
            playoff_assists INTEGER,
            playoff_points  INTEGER,
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
    con.execute("ALTER TABLE raw_player_stats ADD COLUMN IF NOT EXISTS playoff_games_played INTEGER")
    con.execute("ALTER TABLE raw_player_stats ADD COLUMN IF NOT EXISTS playoff_assists INTEGER")
    con.execute("ALTER TABLE raw_player_stats ADD COLUMN IF NOT EXISTS playoff_points INTEGER")


def get_seasons(con):
    rows = con.execute(
        "SELECT DISTINCT season FROM raw_play_by_play ORDER BY season"
    ).fetchall()
    return [r[0] for r in rows]


def is_season_complete(season_id):
    return (season_id % 10000) < datetime.now(timezone.utc).year


def extract_season(con, season_id):
    if is_season_complete(season_id):
        existing, missing_playoff_stats = con.execute(
            """SELECT COUNT(*), COUNT(*) FILTER (
                   WHERE playoff_games_played IS NULL
                      OR playoff_assists IS NULL
                      OR playoff_points IS NULL
               )
               FROM raw_player_stats WHERE season_id = ?""",
            [season_id],
        ).fetchone()
        if existing > 0 and missing_playoff_stats == 0:
            logger.info("Season %d: skipped (%d skaters cached)", season_id, existing)
            return None

    regular = get_stats(
        f"/skater/summary?limit=-1&isAggregate=true&cayenneExp=seasonId={season_id}%20and%20gameTypeId=2"
    ).get("data", [])
    playoffs = get_stats(
        f"/skater/summary?limit=-1&isAggregate=true&cayenneExp=seasonId={season_id}%20and%20gameTypeId=3"
    ).get("data", [])
    regular_by_id = {s["playerId"]: s for s in regular}
    playoff_by_id = {s["playerId"]: s for s in playoffs}

    rows = []
    for player_id in sorted(regular_by_id.keys() | playoff_by_id.keys()):
        regular_stats = regular_by_id.get(player_id, {})
        playoff_stats = playoff_by_id.get(player_id, {})
        player_info = regular_stats or playoff_stats
        rows.append((
            player_id,
            season_id,
            player_info.get("teamAbbrevs", ""),
            player_info.get("positionCode", ""),
            regular_stats.get("gamesPlayed", 0),
            playoff_stats.get("gamesPlayed", 0),
            playoff_stats.get("assists", 0),
            playoff_stats.get("points", 0),
            regular_stats.get("goals", 0),
            regular_stats.get("assists", 0),
            regular_stats.get("points", 0),
            regular_stats.get("plusMinus", 0),
            regular_stats.get("ppGoals", 0),
            regular_stats.get("ppPoints", 0),
            regular_stats.get("shGoals", 0),
            regular_stats.get("shPoints", 0),
            regular_stats.get("shots", 0),
            regular_stats.get("shootingPct"),
            regular_stats.get("timeOnIcePerGame"),
            datetime.now(timezone.utc),
        ))

    con.execute("BEGIN")
    try:
        con.execute("DELETE FROM raw_player_stats WHERE season_id = ?", [season_id])
        con.executemany(
            """
            INSERT INTO raw_player_stats (
                player_id, season_id, team_abbrev, position,
                games_played, playoff_games_played, playoff_assists, playoff_points,
                goals, assists, points, plus_minus,
                pp_goals, pp_points, sh_goals, sh_points,
                shots, shooting_pct, toi_per_game, ingested_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            rows,
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
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
