import os
import sqlite3
from contextlib import contextmanager


def get_dsn() -> str:
    return os.getenv("DATABASE_URL", ":memory:")


@contextmanager
def get_connection():
    conn = sqlite3.connect(get_dsn())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(cursor) -> dict | None:
    row = cursor.fetchone()
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    if isinstance(row, sqlite3.Row):
        return {k: row[k] for k in row.keys()}
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))


def fetch_all(cursor) -> list[dict]:
    rows = cursor.fetchall()
    if not rows:
        return []
    if isinstance(rows[0], dict):
        return rows
    if isinstance(rows[0], sqlite3.Row):
        return [{k: r[k] for k in r.keys()} for r in rows]
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in rows]
