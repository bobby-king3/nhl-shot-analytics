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


def get_all_shooter_ids(con):
    rows = con.execute("""
        SELECT DISTINCT shooter_id
        FROM raw_play_by_play
        WHERE shooter_id IS NOT NULL
    """).fetchall()
    return [r[0] for r in rows]


def get_needs_update(con):
    rows = con.execute("""
        SELECT player_id FROM raw_players WHERE height_in IS NULL
    """).fetchall()
    return {r[0] for r in rows}


def fetch_player(player_id):
    try:
        data = get(f"/player/{player_id}/landing")
        return {
            "player_id":      player_id,
            "first_name":     data.get("firstName", {}).get("default"),
            "last_name":      data.get("lastName", {}).get("default"),
            "position":       data.get("position"),
            "headshot_url":   data.get("headshot"),
            "team_id":        data.get("currentTeamId"),
            "team_abbrev":    data.get("currentTeamAbbrev"),
            "is_active":      data.get("isActive", False),
            "sweater_number": data.get("sweaterNumber"),
            "height_in":      data.get("heightInInches"),
            "weight_lbs":     data.get("weightInPounds"),
            "birth_date":     data.get("birthDate"),
            "birth_city":     (data.get("birthCity") or {}).get("default"),
            "birth_country":  data.get("birthCountry"),
            "shoots_catches": data.get("shootsCatches"),
        }
    except Exception as e:
        print(f"  Warning: could not fetch player {player_id}: {e}")
        return None


def main():
    con = get_connection()
    create_table(con)

    all_ids = get_all_shooter_ids(con)
    needs_update = get_needs_update(con)

    # New players not yet in table at all
    already_fetched = {
        r[0] for r in con.execute("SELECT player_id FROM raw_players").fetchall()
    }
    new_ids = [pid for pid in all_ids if pid not in already_fetched]
    to_fetch = new_ids + [pid for pid in all_ids if pid in needs_update]

    print(f"Total shooters in DB:  {len(all_ids)}")
    print(f"New (never fetched):   {len(new_ids)}")
    print(f"Missing bio data:      {len(needs_update)}")
    print(f"To fetch:              {len(to_fetch)}")

    ingested_at = datetime.now(timezone.utc)
    inserted = 0

    for i, player_id in enumerate(to_fetch, 1):
        player = fetch_player(player_id)
        if not player:
            continue

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
        inserted += 1

        if i % 50 == 0:
            print(f"  [{i}/{len(to_fetch)}] fetched {inserted} players...")

    con.close()
    print(f"Done. Inserted/updated {inserted} players.")


if __name__ == "__main__":
    main()
