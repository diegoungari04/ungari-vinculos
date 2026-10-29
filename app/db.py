"""Camada de dados (SQLite). Caminho do arquivo via DATABASE_PATH."""
import os
import sqlite3
import json
from pathlib import Path

DB_PATH = os.environ.get("DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "data" / "vinculos.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
  area_id INTEGER REFERENCES areas(id) ON DELETE SET NULL,
  manager_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  job_title TEXT,
  role TEXT NOT NULL DEFAULT 'colaborador',
  password_hash TEXT,
  invite_token TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS instruments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data TEXT NOT NULL,
  note TEXT,
  created_by INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  active INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS campaigns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  company_id INTEGER NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  instrument_id INTEGER NOT NULL REFERENCES instruments(id),
  status TEXT NOT NULL DEFAULT 'aberta',
  deadline TEXT,
  created_by INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS assignments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pendente',
  answers TEXT,
  result TEXT,
  completed_at TEXT,
  UNIQUE(campaign_id, user_id)
);
"""


def conn():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init():
    with conn() as c:
        c.executescript(SCHEMA)


def q(sql, args=(), one=False):
    with conn() as c:
        rows = [dict(r) for r in c.execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows


def x(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def jload(s, default=None):
    return json.loads(s) if s else default
