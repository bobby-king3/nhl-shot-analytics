import os
import subprocess
from pathlib import Path

from extract.extract_games import main as run_extract_games
from extract.extract_play_by_play import main as run_extract_play_by_play
from extract.extract_players import main as run_extract_players
from extract.extract_skater_stats import main as run_extract_skater_stats

ROOT = Path(__file__).parent.parent
DBT_DIR = ROOT / "transform" / "dbt_project"


def section(label):
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def run_dbt(command):
    result = subprocess.run(
        ["dbt", command, "--profiles-dir", str(DBT_DIR), "--project-dir", str(DBT_DIR)],
        cwd=ROOT,
        # dbt-duckdb reads motherduck_token (lowercase) from the environment
        env={**os.environ, "motherduck_token": os.environ.get("MOTHERDUCK_TOKEN", "")},
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt {command} failed (exit {result.returncode})")


def main():
    print("=== NHL Shot Intelligence Pipeline ===")

    section("1/5  Extract games")
    run_extract_games()

    section("2/5  Extract play-by-play")
    run_extract_play_by_play()

    section("3/5  Extract players")
    run_extract_players()

    section("4/5  Extract skater stats")
    run_extract_skater_stats()

    section("5/5  dbt (deps → run → test)")
    run_dbt("deps")
    run_dbt("run")
    run_dbt("test")

    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    main()