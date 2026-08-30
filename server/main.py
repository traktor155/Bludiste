# -*- coding: utf-8 -*-
"""Leaderboard server pro hru Únik před příšerkou.

Spuštění:  uvicorn main:app --reload --host 0.0.0.0 --port 8000
Dokumentace API se sama vygeneruje na http://127.0.0.1:8000/docs
"""

import os
import sqlite3
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "scores.db"))

app = FastAPI(title="Únik před příšerkou – leaderboard", version="1.0")


# ---------- databáze ----------
def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS players (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                score      INTEGER NOT NULL,
                level      INTEGER NOT NULL DEFAULT 1,
                created_at TEXT    NOT NULL
            )
        """)
        # index kvůli rychlému žebříčku
        con.execute("CREATE INDEX IF NOT EXISTS idx_score ON players(score DESC)")


init_db()


# ---------- modely ----------
class ScoreIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    score: int = Field(..., ge=0, le=10_000_000)
    level: int = Field(1, ge=1, le=1000)

    @field_validator("name")
    @classmethod
    def clean_name(cls, v: str) -> str:
        v = " ".join(v.split())            # zbavíme se přebytečných mezer
        if not v:
            raise ValueError("jméno nesmí být prázdné")
        return v[:20]


class ScoreOut(BaseModel):
    id: int
    name: str
    score: int
    level: int
    created_at: str


# ---------- API ----------
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/score", response_model=ScoreOut, status_code=201)
def post_score(s: ScoreIn):
    """Uloží jeden výsledek hry."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db() as con:
        cur = con.execute(
            "INSERT INTO players (name, score, level, created_at) VALUES (?, ?, ?, ?)",
            (s.name, s.score, s.level, now))
        row = con.execute("SELECT * FROM players WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/leaderboard", response_model=list[ScoreOut])
def leaderboard(limit: int = 10, best_per_player: bool = True):
    """Nejlepší výsledky. best_per_player = jen jeden (nejlepší) záznam na hráče."""
    if not 1 <= limit <= 100:
        raise HTTPException(400, "limit musí být 1–100")
    if best_per_player:
        sql = """
            SELECT id, name, MAX(score) AS score, level, created_at
            FROM players GROUP BY LOWER(name)
            ORDER BY score DESC, created_at ASC LIMIT ?
        """
    else:
        sql = """
            SELECT id, name, score, level, created_at
            FROM players ORDER BY score DESC, created_at ASC LIMIT ?
        """
    with db() as con:
        rows = con.execute(sql, (limit,)).fetchall()
    return [dict(r) for r in rows]


@app.get("/player/{name}", response_model=list[ScoreOut])
def player_history(name: str, limit: int = 20):
    """Všechny hry jednoho hráče – hezky se z toho dělá graf pokroku."""
    with db() as con:
        rows = con.execute(
            "SELECT * FROM players WHERE LOWER(name) = LOWER(?) "
            "ORDER BY created_at DESC LIMIT ?", (name, limit)).fetchall()
    return [dict(r) for r in rows]


@app.get("/", response_class=HTMLResponse)
def home():
    """Žebříček v prohlížeči – aby ho děti mohly ukázat i bez hry."""
    rows = leaderboard(limit=10)
    medals = ["🥇", "🥈", "🥉"]
    items = "".join(
        "<tr><td>%s</td><td>%s</td><td>%d</td><td>%d</td></tr>" % (
            medals[i] if i < 3 else str(i + 1) + ".",
            _esc(r["name"]), r["score"], r["level"])
        for i, r in enumerate(rows))
    return """<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>Únik před příšerkou – žebříček</title>
<meta http-equiv="refresh" content="10">
<style>
 body{background:#121628;color:#eef2ff;font-family:system-ui,sans-serif;
      display:flex;justify-content:center;padding:40px}
 .card{background:#1c2240;padding:28px 40px;border-radius:16px;min-width:420px}
 h1{color:#ffd166;margin:0 0 18px;font-size:26px}
 table{width:100%%;border-collapse:collapse;font-size:20px}
 td{padding:8px 10px;border-bottom:1px solid #2a3255}
 td:nth-child(3){text-align:right;color:#6ad68f;font-weight:700}
 td:nth-child(4){text-align:right;color:#8b95bd}
 .empty{color:#8b95bd}
</style></head><body><div class="card">
<h1>🏆 Nejlepší hráči</h1>
%s
</div></body></html>""" % (
        "<table><tr><td></td><td>hráč</td><td>body</td><td>kolo</td></tr>%s</table>" % items
        if rows else '<p class="empty">Zatím žádné skóre. Zahraj si!</p>')


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))
