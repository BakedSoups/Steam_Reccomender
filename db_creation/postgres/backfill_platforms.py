"""Import Steam OS flags without rebuilding games or recommendation candidates."""

from __future__ import annotations

import json

from db_creation.paths import metadata_db_path
from db_creation.postgres.load_from_sqlite import load_platform_rows, open_sqlite_readonly, postgres_dsn
from db_creation.precompute_candidates import load_project_env


def main() -> int:
    import psycopg

    load_project_env()
    metadata = open_sqlite_readonly(metadata_db_path())
    try:
        platforms = load_platform_rows(metadata)
    finally:
        metadata.close()
    if not platforms:
        raise RuntimeError("Metadata contains no platform records; refusing to clear existing compatibility data")

    with psycopg.connect(postgres_dsn()) as connection:
        with connection.cursor() as cursor:
            cursor.execute("ALTER TABLE games ADD COLUMN IF NOT EXISTS platforms JSONB")
            cursor.execute("CREATE TEMP TABLE platform_import (appid BIGINT PRIMARY KEY, platforms JSONB) ON COMMIT DROP")
            with cursor.copy("COPY platform_import (appid, platforms) FROM STDIN") as copy:
                for appid, flags in platforms.items():
                    copy.write_row((appid, json.dumps(flags)))
            cursor.execute("""
                UPDATE games g SET platforms = p.platforms
                FROM platform_import p WHERE g.appid = p.appid
                AND g.platforms IS DISTINCT FROM p.platforms
            """)
            updated = cursor.rowcount
            cursor.execute("""
                SELECT count(*), count(platforms) FROM games
            """)
            total, known = cursor.fetchone()
        connection.commit()
    print(f"Platforms updated={updated} known={known} unknown={total-known} total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
