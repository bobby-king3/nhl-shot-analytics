import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DBT_DIR = ROOT / "transform" / "dbt_project"


def section(label):
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")


def run_dbt(command):
    result = subprocess.run(
        [
            sys.executable, "-m", "dbt", command,
            "--profiles-dir", str(DBT_DIR),
            "--project-dir", str(DBT_DIR),
        ],
        cwd=ROOT,
        # dbt-duckdb reads motherduck_token (lowercase) from the environment
        env={**os.environ, "motherduck_token": os.environ.get("MOTHERDUCK_TOKEN", "")},
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt {command} failed (exit {result.returncode})")


def main():
    print("=== NHL Shot Intelligence Pipeline ===")

    section("1/4  Extract games")
    from extract.extract_games import main as _games
    _games()

    section("2/4  Extract play-by-play")
    from extract.extract_play_by_play import main as _pbp
    _pbp()

    section("3/4  Extract players")
    from extract.extract_players import main as _players
    _players()

    section("4/4  dbt (deps → run → test)")
    run_dbt("deps")
    run_dbt("run")
    run_dbt("test")

    print("\n=== Pipeline complete ===")


if __name__ == "__main__":
    main()
