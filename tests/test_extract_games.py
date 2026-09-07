import unittest
from datetime import date, datetime
from unittest.mock import patch

import duckdb

from extract.extract_games import (
    HISTORY_START_DATE,
    create_table,
    fetch_all_games,
    game_to_row,
    get_schedule_request_dates,
    get_schedule_window,
    upsert_games,
)


def completed_game(game_id, home_score, start_date="2026-09-01", away_score=2):
    return {
        "id": game_id,
        "season": 20252026,
        "gameType": 2,
        "gameState": "OFF",
        "startTimeUTC": f"{start_date}T00:00:00Z",
        "venue": {"default": "Test Arena"},
        "homeTeam": {"id": 1, "abbrev": "AAA", "score": home_score},
        "awayTeam": {"id": 2, "abbrev": "BBB", "score": away_score},
        "gameOutcome": {"lastPeriodType": "REG"},
    }


class ExtractGamesTests(unittest.TestCase):
    def setUp(self):
        self.con = duckdb.connect(":memory:")
        create_table(self.con)

    def tearDown(self):
        self.con.close()

    def test_empty_table_automatically_uses_full_history(self):
        today = date(2026, 9, 6)

        self.assertEqual(
            get_schedule_window(self.con, today=today),
            (HISTORY_START_DATE, today),
        )

    def test_incremental_window_recovers_from_last_stored_game(self):
        observed_at = datetime(2026, 8, 30)
        upsert_games(self.con, [
            game_to_row(completed_game(1, 2, "2026-08-31"), "2026-08-30", observed_at)
        ])

        start, end = get_schedule_window(self.con, today=date(2026, 9, 6))

        self.assertEqual(start, date(2026, 8, 23))
        self.assertEqual(end, date(2026, 9, 6))
        self.assertEqual(
            list(get_schedule_request_dates(start, end)),
            [date(2026, 8, 23), date(2026, 8, 30), date(2026, 9, 6)],
        )

    def test_incremental_window_expands_after_a_long_outage(self):
        observed_at = datetime(2026, 8, 1)
        upsert_games(self.con, [
            game_to_row(completed_game(1, 2, "2026-08-02"), "2026-08-01", observed_at)
        ])

        start, end = get_schedule_window(self.con, today=date(2026, 9, 6))

        self.assertEqual(start, date(2026, 7, 25))
        self.assertEqual(end, date(2026, 9, 6))

    def test_full_backfill_uses_single_historical_range(self):
        observed_at = datetime(2026, 9, 1)
        upsert_games(self.con, [
            game_to_row(completed_game(1, 2), "2026-09-01", observed_at)
        ])

        self.assertEqual(
            get_schedule_window(self.con, full_backfill=True, today=date(2026, 9, 6)),
            (HISTORY_START_DATE, date(2026, 9, 6)),
        )

    @patch("extract.extract_games.get")
    def test_full_backfill_fetches_the_complete_range(self, mock_get):
        mock_get.return_value = {"gameWeek": []}
        today = HISTORY_START_DATE.replace(day=24)

        result = fetch_all_games(self.con, full_backfill=True, today=today)

        self.assertEqual(result["request_count"], 3)
        self.assertEqual(mock_get.call_count, 3)

    def test_upsert_preserves_ingested_at_and_only_updates_corrections(self):
        first_seen = datetime(2026, 8, 1)
        seen_again = datetime(2026, 9, 1)
        corrected_at = datetime(2026, 9, 2)

        original = game_to_row(completed_game(1, 2), "2026-09-01", first_seen)
        unchanged = game_to_row(completed_game(1, 2), "2026-09-01", seen_again)
        corrected = game_to_row(completed_game(1, 3), "2026-09-01", corrected_at)

        self.assertEqual(upsert_games(self.con, [original]), (1, 0, 0))
        self.assertEqual(upsert_games(self.con, [unchanged]), (0, 0, 1))
        self.assertEqual(
            self.con.execute(
                "SELECT ingested_at, updated_at FROM raw_games WHERE game_id = 1"
            ).fetchone(),
            (first_seen, first_seen),
        )

        self.assertEqual(upsert_games(self.con, [corrected]), (0, 1, 0))
        self.assertEqual(
            self.con.execute(
                "SELECT home_score, ingested_at, updated_at FROM raw_games WHERE game_id = 1"
            ).fetchone(),
            (3, first_seen, corrected_at),
        )

    @patch("extract.extract_games.get")
    def test_incremental_run_deduplicates_overlaps_and_filters_unfinished_games(self, mock_get):
        observed_at = datetime(2026, 8, 30)
        upsert_games(self.con, [
            game_to_row(completed_game(1, 2, "2026-08-31"), "2026-08-30", observed_at)
        ])

        mock_get.side_effect = [
            {"gameWeek": [{"date": "2026-08-30", "games": [completed_game(1, 2, "2026-08-31")]}]},
            {"gameWeek": [{"date": "2026-08-30", "games": [
                completed_game(1, 3, "2026-08-30"),
                completed_game(2, 4),
            ]}]},
            {"gameWeek": [{"date": "2026-09-01", "games": [
                completed_game(2, 4),
                {"id": 3, "gameState": "FUT"},
            ]}]},
        ]

        result = fetch_all_games(self.con, today=date(2026, 9, 6))

        self.assertEqual(result, {
            "request_count": 3,
            "games_found": 2,
            "inserted": 1,
            "updated": 1,
            "unchanged": 0,
        })
        self.assertEqual(mock_get.call_count, 3)
        self.assertEqual(
            self.con.execute(
                "SELECT game_id, home_score FROM raw_games ORDER BY game_id"
            ).fetchall(),
            [(1, 3), (2, 4)],
        )

    def test_game_date_uses_schedule_bucket_instead_of_utc_date(self):
        row = game_to_row(
            completed_game(1, 2, start_date="2026-01-09"),
            "2026-01-08",
            datetime(2026, 1, 9),
        )

        self.assertEqual(row[3], date(2026, 1, 8))
        self.assertEqual(row[4], datetime(2026, 1, 9))

    def test_create_table_migrates_existing_updated_at_values(self):
        self.con.execute("ALTER TABLE raw_games DROP COLUMN updated_at")
        ingested_at = datetime(2026, 8, 1)
        self.con.execute("""
            INSERT INTO raw_games VALUES (
                1, 20252026, 2, '2026-08-01', '2026-08-01T00:00:00', 'Test Arena',
                1, 'AAA', 3, 2, 'BBB', 2, 'REG', ?
            )
        """, [ingested_at])

        create_table(self.con)

        self.assertEqual(
            self.con.execute(
                "SELECT ingested_at, updated_at FROM raw_games WHERE game_id = 1"
            ).fetchone(),
            (ingested_at, ingested_at),
        )


if __name__ == "__main__":
    unittest.main()
