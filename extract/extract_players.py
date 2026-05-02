import logging
from datetime import datetime, timezone
from extract.connection import get_connection
from extract.logging_config import setup_logging
from extract.nhl_client.nhl_api import get

logger = logging.getLogger(__name__)


def create_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_players (
            player_id       INTEGER PRIMARY KEY,
            first_name      VARCHAR,
            last_name       VARCHAR,
            position        VARCHAR,
            headshot_url    VARCHAR,
            team_id         INTEGER,
            team_abbrev     VARCHAR,
            is_active       BOOLEAN,
            sweater_number  INTEGER,
            height_in       INTEGER,
            weight_lbs      INTEGER,
            birth_date      VARCHAR,
            birth_city      VARCHAR,
            birth_country   VARCHAR,
            shoots_catches  VARCHAR,
            ingested_at     TIMESTAMP
        )
    """)


def get_current_teams():
    data = get("/standings/now")
    return [s["teamAbbrev"]["default"] for s in data.get("standings", [])]


def fetch_roster(team_abbrev):
    try:
        data = get(f"/roster/{team_abbrev}/current")
    except Exception as e:
        logger.warning("Could not fetch roster for %s: %s", team_abbrev, e)
        return []

    players = []
    for group in ("forwards", "defensemen", "goalies"):
        for p in data.get(group, []):
            players.append({
                "player_id":      p["id"],
                "first_name":     p.get("firstName", {}).get("default"),
                "last_name":      p.get("lastName", {}).get("default"),
                "position":       p.get("positionCode"),
                "headshot_url":   p.get("headshot"),
                "team_id":        None,
                "team_abbrev":    team_abbrev,
                "is_active":      True,
                "sweater_number": p.get("sweaterNumber"),
                "height_in":      p.get("heightInInches"),
                "weight_lbs":     p.get("weightInPounds"),
                "birth_date":     p.get("birthDate"),
                "birth_city":     (p.get("birthCity") or {}).get("default"),
                "birth_country":  p.get("birthCountry"),
                "shoots_catches": p.get("shootsCatches"),
            })
    return players


def upsert_all(con, players, ingested_at):
    player_ids = [p["player_id"] for p in players]
    con.execute(f"DELETE FROM raw_players WHERE player_id IN ({','.join('?' * len(player_ids))})", player_ids)
    con.executemany("""
        INSERT INTO raw_players (
            player_id, first_name, last_name, position, headshot_url,
            team_id, team_abbrev, is_active, sweater_number,
            height_in, weight_lbs, birth_date, birth_city, birth_country,
            shoots_catches, ingested_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [
        (
            p["player_id"], p["first_name"], p["last_name"], p["position"],
            p["headshot_url"], p["team_id"], p["team_abbrev"], p["is_active"],
            p["sweater_number"], p["height_in"], p["weight_lbs"], p["birth_date"],
            p["birth_city"], p["birth_country"], p["shoots_catches"], ingested_at,
        )
        for p in players
    ])


def main():
    con = get_connection()
    create_table(con)

    teams = get_current_teams()
    logger.info("Teams to process: %d", len(teams))

    ingested_at = datetime.now(timezone.utc)
    all_players = []

    for team in teams:
        players = fetch_roster(team)
        all_players.extend(players)
        logger.info("  %s: %d players", team, len(players))

    upsert_all(con, all_players, ingested_at)
    con.close()
    logger.info("Players extraction complete. Inserted/updated %d players across %d teams.", len(all_players), len(teams))


if __name__ == "__main__":
    setup_logging()
    main()
