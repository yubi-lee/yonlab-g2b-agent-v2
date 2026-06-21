import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL,
    keyword TEXT,
    start_date TEXT,
    end_date TEXT,
    num_rows INTEGER,
    source_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    message TEXT NOT NULL DEFAULT '',
    error_code TEXT,
    service_key_exposed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    rank INTEGER NOT NULL,
    notice_id TEXT NOT NULL,
    title TEXT NOT NULL,
    agency TEXT NOT NULL,
    budget_amount INTEGER,
    deadline TEXT,
    total_score INTEGER NOT NULL,
    recommendation_label TEXT NOT NULL,
    risk_count INTEGER NOT NULL DEFAULT 0,
    top_reasons_json TEXT NOT NULL DEFAULT '[]',
    risk_summaries_json TEXT NOT NULL DEFAULT '[]',
    detail_url TEXT NOT NULL DEFAULT '',
    report_path TEXT NOT NULL DEFAULT '',
    raw_json_path TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(run_id, notice_id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    notice_id TEXT NOT NULL,
    title TEXT NOT NULL,
    report_path TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(run_id, notice_id, report_path)
);
"""


def connect_database(db_path: str | Path) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: str | Path) -> None:
    with connect_database(db_path) as connection:
        connection.executescript(SCHEMA_SQL)
