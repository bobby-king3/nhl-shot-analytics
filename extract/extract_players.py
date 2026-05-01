import sys
sys.path.append(".")

from datetime import datetime, timezone
from extract.connection import get_connection
from extract.nhl_client.nhl_api import get


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
        print(f"  Warning: could not fetch roster for {team_abbrev}: {e}")
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


def upsert(con, player, ingested_at):
    con.execute("DELETE FROM raw_players WHERE player_id = ?", [player["player_id"]])
    con.execute("""
        INSERT INTO raw_players (
            player_id, first_name, last_name, position, headshot_url,
            team_id, team_abbrev, is_active, sweater_number,
            height_in, weight_lbs, birth_date, birth_city, birth_country,
            shoots_catches, ingested_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, [
        player["player_id"],
        player["first_name"],
        player["last_name"],
        player["position"],
        player["headshot_url"],
        player["team_id"],
        player["team_abbrev"],
        player["is_active"],
        player["sweater_number"],
        player["height_in"],
        player["weight_lbs"],
        player["birth_date"],
        player["birth_city"],
        player["birth_country"],
        player["shoots_catches"],
        ingested_at,
    ])


def main():
    con = get_connection()
    create_table(con)

    teams = get_current_teams()
    print(f"Teams to process: {len(teams)}")

    ingested_at = datetime.now(timezone.utc)
    total = 0

    for team in teams:
        players = fetch_roster(team)
        for player in players:
            upsert(con, player, ingested_at)
        total += len(players)
        print(f"  {team}: {len(players)} players")

    con.close()
    print(f"Done. Inserted/updated {total} players across {len(teams)} teams.")


if __name__ == "__main__":
    main()
