import csv
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

import duckdb
import httpx

from extract.extract_moneypuck import SHOT_COLUMNS, main, refresh


def make_zip(path, rows):
    with tempfile.TemporaryDirectory() as temp_dir:
        csv_path = Path(temp_dir) / "shots_2025.csv"
        with csv_path.open("w", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=SHOT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        with zipfile.ZipFile(path, "w") as archive:
            archive.write(csv_path, csv_path.name)


def shot(shot_id, season=2025):
    return {
        "game_id": 20001, "shotID": shot_id, "shooterPlayerId": 8478542,
        "shooterName": "Player", "period": 1, "time": 15,
        "xCordAdjusted": -58, "yCordAdjusted": -22, "shotType": "WRIST",
        "event": "SHOT", "xGoal": 0.1, "shotRush": 0,
        "shotRebound": 0, "isPlayoffGame": 0, "season": season, "team": "HOME",
    }


class MoneyPuckIngestionTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect(":memory:")
        self.temp = tempfile.TemporaryDirectory()
        self.zip_path = Path(self.temp.name) / "shots_2025.zip"
        self.url = "https://peter-tanner.com/moneypuck/downloads/shots_2025.zip"

    def tearDown(self):
        self.con.close()
        self.temp.cleanup()

    def load_zip(self, rows, version="v1"):
        make_zip(self.zip_path, rows)
        response = httpx.Response(
            200, content=self.zip_path.read_bytes(), headers={"ETag": version},
            request=httpx.Request("GET", self.url),
        )
        with patch("extract.extract_moneypuck.httpx.get", return_value=response):
            return refresh(self.con, self.url)

    def test_refresh_replaces_only_target_season_and_skips_unchanged_file(self):
        self.assertEqual(self.load_zip([shot(1), shot(2)]), 2)
        self.con.execute("""
            INSERT INTO raw_moneypuck_shots (shotID, season) VALUES (99, 2024)
        """)

        self.assertEqual(self.load_zip([shot(1), shot(3)], version="v2"), 2)
        self.assertEqual(
            self.con.execute("SELECT shotID FROM raw_moneypuck_shots WHERE season = 2025 ORDER BY shotID").fetchall(),
            [(1,), (3,)],
        )
        self.assertEqual(
            self.con.execute("SELECT count(*) FROM raw_moneypuck_shots WHERE season = 2024").fetchone()[0], 1
        )
        self.assertEqual(self.load_zip([shot(1), shot(3)], version="v2"), 0)
        self.assertEqual(
            self.con.execute("SELECT count(*) FROM raw_moneypuck_shots WHERE season = 2025").fetchone()[0], 2
        )

    def test_bad_season_does_not_replace_previous_rows(self):
        self.load_zip([shot(1)])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.load_zip([shot(2, season=2024)], version="v2")
        self.assertEqual(
            self.con.execute("SELECT shotID FROM raw_moneypuck_shots WHERE season = 2025").fetchall(),
            [(1,)],
        )

    def test_conditional_download_sends_file_version_and_handles_304(self):
        self.load_zip([shot(1)])
        with patch("extract.extract_moneypuck.httpx.get", return_value=httpx.Response(304)) as get:
            self.assertEqual(refresh(self.con, self.url), 0)
        self.assertEqual(get.call_args.kwargs["headers"]["If-None-Match"], "v1")

    def test_new_nhl_season_requires_a_published_url_update(self):
        self.con.execute("CREATE TABLE raw_play_by_play (game_id BIGINT)")
        self.con.execute("INSERT INTO raw_play_by_play VALUES (2026020001)")
        with self.assertRaisesRegex(ValueError, "update MONEYPUCK_SHOTS_URL"):
            refresh(self.con, self.url)

    def test_short_file_does_not_erase_existing_season(self):
        self.load_zip([shot(i) for i in range(100)])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.load_zip([shot(i) for i in range(5)], version="v2")
        self.assertEqual(
            self.con.execute("SELECT count(*) FROM raw_moneypuck_shots WHERE season = 2025").fetchone()[0],
            100,
        )

    def test_download_url_is_required_but_host_is_configurable(self):
        with patch.dict(os.environ, {"MONEYPUCK_SHOTS_URL": ""}):
            with self.assertRaisesRegex(ValueError, "Set MONEYPUCK_SHOTS_URL"):
                main()

        self.load_zip([shot(1)])
        response = httpx.Response(
            200, content=self.zip_path.read_bytes(), request=httpx.Request("GET", self.url)
        )
        with patch("extract.extract_moneypuck.httpx.get", return_value=response) as get:
            self.assertEqual(refresh(self.con, "https://downloads.example.org/shots_2025.zip"), 0)
        self.assertEqual(get.call_args.kwargs["headers"], {})


if __name__ == "__main__":
    unittest.main()
