import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras


def get_dsn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return dsn


@contextmanager
def get_connection():
    conn = psycopg2.connect(get_dsn())
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
    columns = [desc[0] for desc in cursor.description]
    return dict(zip(columns, row))