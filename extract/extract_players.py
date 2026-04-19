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
            ingested_at     TIMESTAMP
        )
    """)


def get_all_shooter_ids(con):
    rows = con.execute("""
        SELECT DISTINCT shooter_id
        FROM raw_play_by_play
        WHERE shooter_id IS NOT NULL
    """).fetchall()
    return [r[0] for r in rows]


def get_already_fetched(con):
    rows = con.execute("SELECT player_id FROM raw_players").fetchall()
    return {r[0] for r in rows}


def fetch_player(player_id):
    try:
        data = get(f"/player/{player_id}/landing")
        return {
            "player_id":    player_id,
            "first_name":   data.get("firstName", {}).get("default"),
            "last_name":    data.get("lastName", {}).get("default"),
            "position":     data.get("position"),
            "headshot_url": data.get("headshot"),
            "team_id":      data.get("currentTeamId"),
            "team_abbrev":  data.get("currentTeamAbbrev"),
            "is_active":    data.get("isActive", False),
        }
    except Exception as e:
        print(f"  Warning: could not fetch player {player_id}: {e}")
        return None


def main():
    con = get_connection()
    create_table(con)

    all_ids = get_all_shooter_ids(con)
    already_fetched = get_already_fetched(con)
    to_fetch = [pid for pid in all_ids if pid not in already_fetched]

    print(f"Total shooters in DB:  {len(all_ids)}")
    print(f"Already fetched:       {len(already_fetched)}")
    print(f"To fetch:              {len(to_fetch)}")

    ingested_at = datetime.now(timezone.utc)
    inserted = 0

    for i, player_id in enumerate(to_fetch, 1):
        player = fetch_player(player_id)
        if not player:
            continue

        con.execute("""
            INSERT OR REPLACE INTO raw_players VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            player["player_id"],
            player["first_name"],
            player["last_name"],
            player["position"],
            player["headshot_url"],
            player["team_id"],
            player["team_abbrev"],
            player["is_active"],
            ingested_at,
        ])
        inserted += 1

        if i % 50 == 0:
            print(f"  [{i}/{len(to_fetch)}] fetched {inserted} players...")

    con.close()
    print(f"Done. Inserted {inserted} players.")


if __name__ == "__main__":
    main()
