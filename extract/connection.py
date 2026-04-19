import os
import duckdb

LOCAL_DB_PATH = "data/nhl.duckdb"


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    token = os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        os.environ.setdefault("motherduck_token", token)
        return duckdb.connect("md:nhl", read_only=read_only)
    return duckdb.connect(LOCAL_DB_PATH, read_only=read_only)
