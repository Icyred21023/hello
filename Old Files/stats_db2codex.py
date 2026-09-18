# stats_db.py
# SQLite storage + percentile leaderboard lookup for Player/Hero stats.
#
# Drop this file next to your other modules, then in gui.py after you build players:
#   from stats_db import StatsDB
#   db = StatsDB()
#   db.upsert_players(players)                 # optional: persist this run
#   pct = db.stat_percentile("Magik","kd_ratio", 9.09)   # 0% best, 100% worst
#   db.close()
#
# Notes:
# - Avoids repeating DB writes via player_sig + hero_sig (skips unchanged rows)
# - Percentile works even if you haven't inserted this run yet (you pass stat_value)
from __future__ import annotations
from logging import log
from playerNEW import Player, Hero, Overview
import os
import time
import sqlite3
import hashlib
import re
from dataclasses import dataclass
from typing import Iterable, Optional, Any
import config

from datetime import datetime

def save_list_to_log(data_list, file_path="log.txt", timestamp=True, mode="a"):
    """
    Save list entries to a text log file.

    data_list : list
        List of items to write
    file_path : str
        Path to txt log file
    timestamp : bool
        If True, prepend timestamp
    mode : str
        'a' append (default) or 'w' overwrite
    """

    os.makedirs(os.path.dirname(file_path) or ".", exist_ok=True)

    with open(file_path, mode, encoding="utf-8") as f:
        for item in data_list:
            line = str(item)

            if timestamp:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                line = f"[{ts}] {line}"

            f.write(line + "\n")
# ----------------------------
# Helpers
# ----------------------------



def _db_dir() -> str:
    return config.sqlite_db_dir

def _db_path() -> str:
    return config.sqlite_db_path
def _script_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()

def _now_ts() -> int:
    return int(time.time())

def _as_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _as_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _as_text(x: Any, default: str = "") -> str:
    return str(x) if x is not None else default

def _pct_str_to_float(x: Any) -> float:
    """
    Convert '47%' / 47 / 47.2 to float percent 0..100.
    Returns 0.0 on invalid.
    """
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).strip()
    if not s:
        return 0.0
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        return float(s)
    except Exception:
        return 0.0


def _pct_to_float(pct: Any) -> float:
    """Convert '54%' or 54 or 54.2 to float percent (0..100)."""
    if pct is None:
        return 0.0
    if isinstance(pct, (int, float)):
        return float(pct)
    s = str(pct).strip()
    if s.endswith("%"):
        s = s[:-1].strip()
    try:
        return float(s)
    except Exception:
        return 0.0

# ----------------------------
# DB
# ----------------------------

DEFAULT_DB_DIRNAME = "players_db"
DEFAULT_LOG = "db.txt"
DEFAULT_DB_FILENAME = "players_stats.db"
MIN_HERO_MATCHES = 6
MIN_SECONDS_PLAYED = 14400 # 4 hrs
MIN_SECONDS_OVERVIEW = 18000 # 5 hrs


@dataclass
class DBPaths:
    db_path: str

class StatsDB:
    """
    SQLite DB for storing:
      - Players (one row per player)
      - Player-Hero stats (one row per player per hero)
    Also provides percentile leaderboard lookup:
      - 0% best, 100% worst
    """

    OV_STAT_DIR = {
    "kd_ratio": "desc",
    "kda_ratio": "desc",
    "win_pct": "desc",
    "damage_per_minute": "desc",
    "healing_per_minute": "desc",
    "mvp_pct": "desc",
    "svp_pct": "desc",
    "matches_played": "desc",
    "matches_won": "desc",
    # add others as you like
}

    OV_ALLOWED = {
        "matches_played","matches_won","win_pct",
        "kills","assists","deaths",
        "kd_ratio","kda_ratio",
        "total_damage","total_healing",
        "damage_per_minute","healing_per_minute",
        "total_damage_taken","total_damage_taken_per_minute",
        "last_kills",
        "mvps","mvp_pct","svps","svp_pct",
        "time_played"
    }

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        """
        Add missing columns to an existing table without nuking data.
        columns = { "colname": "SQLTYPE", ... }
        """
        cur = self.conn.cursor()
        existing = {row["name"] for row in cur.execute(f"PRAGMA table_info({table});")}
        for col, sqltype in columns.items():
            if col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sqltype};")

    def overview_percentile(
        self,
        stat_key: str,
        stat_value: float,
        *,
        direction: Optional[str] = None,
        min_samples: int = 50,
    ) -> Optional[float]:
        """
        Percentile across ALL players' overview stats.
        0.0 = best, 100.0 = worst.
        """
        stat_key = (stat_key or "").strip()
        if stat_key not in self.OV_ALLOWED:
            return None

        direction = direction or self.OV_STAT_DIR.get(stat_key, "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"

        cur = self.conn.cursor()
        total = cur.execute(
            f"SELECT COUNT(*) AS n FROM player_overview WHERE {stat_key} IS NOT NULL;",
        ).fetchone()["n"]

        if total < min_samples:
            return None

        if direction == "desc":
            better = cur.execute(
                f"SELECT COUNT(*) AS n FROM player_overview WHERE {stat_key} > ?;",
                (stat_value,),
            ).fetchone()["n"]
        else:
            better = cur.execute(
                f"SELECT COUNT(*) AS n FROM player_overview WHERE {stat_key} < ?;",
                (stat_value,),
            ).fetchone()["n"]

        pct = (better / total) * 100.0
        return round(max(0.0, min(100.0, pct)), 2)


    # Higher is better unless listed otherwise
    STAT_DIR = {
        "kd_ratio": "desc",
        "kda_ratio": "desc",
        "win_pct": "desc",
        "damage_per_minute": "desc",
        "healing_per_minute": "desc",
        "total_damage": "desc",
        "total_healing": "desc",
        "matches_won": "desc",
        "head_kills": "desc",
        "total_mvp": "desc",
        "total_svp": "desc",
        "time_played": "desc",
        "time_played_won": "desc",
        "kills_per_10": "desc",
        "assists_per_10": "desc",
        "average_lifespan": "desc",

        # Example "lower is better":
        # "deaths": "asc",
    }

    # Allowlist to prevent SQL injection (column names must be hardcoded)
    ALLOWED_NUMERIC_COLS = {
        "matches_played", "matches_won", "win_pct",
        "time_played", "time_played_won",
        "kills", "assists", "deaths",
        "kd_ratio", "kda_ratio",
        "total_damage", "total_healing",
        "damage_per_minute", "healing_per_minute",
        "total_damage_taken", "total_damage_taken_per_minute",
        "last_kills", "head_kills",
        "total_mvp", "total_svp",
        "mvp_pct", "svp_pct","kills_per_10","assists_per_10","average_lifespan",
        "last_kills_per_10", "head_kills_per_10", "accuracy", "headshot_accuracy",
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            
            db_path = _db_path()

        self.paths = DBPaths(db_path=db_path)
        self.conn = sqlite3.connect(self.paths.db_path)
        self.conn.row_factory = sqlite3.Row

        # Performance
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA synchronous=NORMAL;")
        self.conn.execute("PRAGMA temp_store=MEMORY;")
        self.conn.execute("PRAGMA foreign_keys=ON;")

        self._init_schema()

    def close(self):
        try:
            self.conn.commit()
        finally:
            self.conn.close()
    def _upsert_player_overview(self, cur: sqlite3.Cursor, player_name: str, ov: Any, now: int) -> None:
        # Pull from your Overview class fields
        matches_played = _as_int(getattr(ov, "matches_played", 0))
        matches_won = _as_int(getattr(ov, "matches_won", 0))
        win_pct = _pct_to_float(getattr(ov, "win_pct", "0%"))

        kills = _as_int(getattr(ov, "kills", 0))
        assists = _as_int(getattr(ov, "assists", 0))
        deaths = _as_int(getattr(ov, "deaths", 0))

        kd_ratio = _as_float(getattr(ov, "kd_ratio", 0.0))
        kda_ratio = _as_float(getattr(ov, "kda_ratio", 0.0))

        total_damage = _as_float(getattr(ov, "total_damage", 0.0))
        total_healing = _as_float(getattr(ov, "total_healing", 0.0))

        damage_per_minute = _as_int(getattr(ov, "damage_per_minute", 0))
        healing_per_minute = _as_int(getattr(ov, "healing_per_minute", 0))

        total_damage_taken = _as_float(getattr(ov, "total_damage_taken", 0.0))
        total_damage_taken_per_minute = _as_int(getattr(ov, "total_damage_taken_per_minute", 0))

        last_kills = _as_int(getattr(ov, "last_kills", 0))

        mvps = _as_int(getattr(ov, "mvps", 0))
        mvp_pct = _pct_to_float(getattr(ov, "mvp_pct", "0%"))
        svps = _as_int(getattr(ov, "svps", 0))
        svp_pct = _pct_to_float(getattr(ov, "svp_pct", "0%"))

        time_played = _as_int(getattr(ov, "time_played", 0))

        overview_sig = _sha1("|".join(map(str, [
            player_name.lower(),
            matches_played, matches_won, win_pct,
            kills, assists, deaths,
            kd_ratio, kda_ratio,
            total_damage, total_healing,
            damage_per_minute, healing_per_minute,
            total_damage_taken, total_damage_taken_per_minute,
            last_kills,
            mvps, mvp_pct, svps, svp_pct,
            time_played
        ])))

        row = cur.execute(
            "SELECT overview_sig FROM player_overview WHERE player_name=?;",
            (player_name,)
        ).fetchone()

        if row is not None and row["overview_sig"] == overview_sig:
            return None  # unchanged

        # Determine insert vs update for op label
        op_kind = "insert" if row is None else "update"

        cur.execute("""
            INSERT INTO player_overview (
                player_name,
                matches_played, matches_won, win_pct,
                kills, assists, deaths,
                kd_ratio, kda_ratio,
                total_damage, total_healing,
                damage_per_minute, healing_per_minute,
                total_damage_taken, total_damage_taken_per_minute,
                last_kills,
                mvps, mvp_pct,
                svps, svp_pct,
                time_played,
                last_updated_ts, overview_sig
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(player_name) DO UPDATE SET
                matches_played=excluded.matches_played,
                matches_won=excluded.matches_won,
                win_pct=excluded.win_pct,
                kills=excluded.kills,
                assists=excluded.assists,
                deaths=excluded.deaths,
                kd_ratio=excluded.kd_ratio,
                kda_ratio=excluded.kda_ratio,
                total_damage=excluded.total_damage,
                total_healing=excluded.total_healing,
                damage_per_minute=excluded.damage_per_minute,
                healing_per_minute=excluded.healing_per_minute,
                total_damage_taken=excluded.total_damage_taken,
                total_damage_taken_per_minute=excluded.total_damage_taken_per_minute,
                last_kills=excluded.last_kills,
                mvps=excluded.mvps,
                mvp_pct=excluded.mvp_pct,
                svps=excluded.svps,
                svp_pct=excluded.svp_pct,
                time_played=excluded.time_played,
                last_updated_ts=excluded.last_updated_ts,
                overview_sig=excluded.overview_sig;
        """, (
            player_name,
            matches_played, matches_won, win_pct,
            kills, assists, deaths,
            kd_ratio, kda_ratio,
            total_damage, total_healing,
            damage_per_minute, healing_per_minute,
            total_damage_taken, total_damage_taken_per_minute,
            last_kills,
            mvps, mvp_pct,
            svps, svp_pct,
            time_played,
            now, overview_sig
        ))

        return {
        "ts": now,
        "table": "player_overview",
        "op": op_kind,
        "pk": {"player_name": player_name},
        "data": {
            "matches_played": matches_played,
            "matches_won": matches_won,
            "win_pct": win_pct,
            "kills": kills,
            "assists": assists,
            "deaths": deaths,
            "kd_ratio": kd_ratio,
            "kda_ratio": kda_ratio,
            "total_damage": total_damage,
            "total_healing": total_healing,
            "damage_per_minute": damage_per_minute,
            "healing_per_minute": healing_per_minute,
            "total_damage_taken": total_damage_taken,
            "total_damage_taken_per_minute": total_damage_taken_per_minute,
            "last_kills": last_kills,
            "mvps": mvps,
            "mvp_pct": mvp_pct,
            "svps": svps,
            "svp_pct": svp_pct,
            "time_played": time_played,
            "last_updated_ts": now,
            "overview_sig": overview_sig,
        }
    }

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS players (
            player_name     TEXT PRIMARY KEY,
            first_seen_ts   INTEGER NOT NULL,
            last_seen_ts    INTEGER NOT NULL,
            season_rank     TEXT,
            best_rank       TEXT,
            is_private      INTEGER DEFAULT 0,
            player_sig      TEXT NOT NULL
        );
        """)
        
        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_heroes (
            player_name     TEXT NOT NULL,
            hero_name       TEXT NOT NULL,

            role            TEXT,

            matches_played  FLOAT,
            matches_won     FLOAT,
            win_pct         REAL,   -- 0..100

            time_played     INTEGER,
            time_played_won INTEGER,

            kills           INTEGER,
            assists         INTEGER,
            deaths          INTEGER,

            kd_ratio        REAL,
            kda_ratio       REAL,

            total_damage    REAL,
            total_healing   REAL,

            damage_per_minute  INTEGER,
            healing_per_minute INTEGER,

            total_damage_taken REAL,
            total_damage_taken_per_minute INTEGER,

            last_kills      INTEGER,
            head_kills      INTEGER,
            average_lifespan FLOAT,
            kills_per_10    FLOAT,
            assists_per_10  FLOAT,
            total_mvp       INTEGER,
            total_svp       INTEGER,

            mvp_pct         REAL,   -- 0..100
            svp_pct         REAL,   -- 0..100
            last_kills_per_10 REAL,
            head_kills_per_10 REAL,
            accuracy REAL,
            headshot_accuracy REAL,

            last_updated_ts INTEGER NOT NULL,
            hero_sig        TEXT NOT NULL,

            PRIMARY KEY (player_name, hero_name),
            FOREIGN KEY (player_name) REFERENCES players(player_name) ON DELETE CASCADE
        );
        """)

        
        self._ensure_columns("player_heroes", {
            "last_kills_per_10": "REAL",
            "head_kills_per_10": "REAL",
            "accuracy": "REAL",
            "headshot_accuracy": "REAL",
        })
        # Generic indexes
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero ON player_heroes(hero_name);")

        cur.execute("""
        CREATE TABLE IF NOT EXISTS player_overview (
            player_name     TEXT PRIMARY KEY,

            matches_played  INTEGER,
            matches_won     INTEGER,
            win_pct         REAL,   -- 0..100

            kills           INTEGER,
            assists         INTEGER,
            deaths          INTEGER,

            kd_ratio        REAL,
            kda_ratio       REAL,

            total_damage    REAL,
            total_healing   REAL,

            damage_per_minute  INTEGER,
            healing_per_minute INTEGER,

            total_damage_taken REAL,
            total_damage_taken_per_minute INTEGER,

            last_kills      INTEGER,

            mvps            INTEGER,
            mvp_pct         REAL,   -- 0..100
            svps            INTEGER,
            svp_pct         REAL,   -- 0..100

            time_played     INTEGER,

            last_updated_ts INTEGER NOT NULL,
            overview_sig    TEXT NOT NULL,

            FOREIGN KEY (player_name) REFERENCES players(player_name) ON DELETE CASCADE
        );
        """)


        # Stat-specific indexes (for fast percentile queries)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_kd ON player_heroes(hero_name, kd_ratio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_kda ON player_heroes(hero_name, kda_ratio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_win ON player_heroes(hero_name, win_pct);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_dpm ON player_heroes(hero_name, damage_per_minute);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_hpm ON player_heroes(hero_name, healing_per_minute);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_kills_per_10 ON player_heroes(hero_name, kills_per_10);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_assists_per_10 ON player_heroes(hero_name, assists_per_10);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_average_lifespan ON player_heroes(hero_name, average_lifespan);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ov_kd ON player_overview(kd_ratio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ov_kda ON player_overview(kda_ratio);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ov_win ON player_overview(win_pct);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ov_dpm ON player_overview(damage_per_minute);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ov_hpm ON player_overview(healing_per_minute);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_lastkills10 ON player_heroes(hero_name, last_kills_per_10);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_headkills10 ON player_heroes(hero_name, head_kills_per_10);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_accuracy ON player_heroes(hero_name, accuracy);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ph_hero_headshotacc ON player_heroes(hero_name, headshot_accuracy);")


        # ---- MIGRATIONS: add new hero stat columns without resetting DB ----
        
        self.conn.commit()

    # ----------------------------
    # Upserts (avoid repeating)
    # ----------------------------
    def upsert_players(self, players: Iterable[Any]) -> list[dict]:
        """
        Upsert all provided Player objects + their Hero objects.
        Returns a list of ops for any actual DB writes (insert/update).
        """
        now = _now_ts()
        cur = self.conn.cursor()
        ops: list[dict] = []
        log = []
        with self.conn:  # one transaction
            for p in players:
                player_name = _as_text(getattr(p, "name", "")).strip()
                if not player_name:
                    continue

                season_rank = _as_text(getattr(p, "season_rank", ""), "")
                best_rank = _as_text(getattr(p, "best_rank", ""), "")
                is_private = 1 if bool(getattr(p, "bPrivate", False)) else 0

                fo = getattr(p, "full_overview", None)
                heroes_all = getattr(fo, "heroes", []) if fo is not None else (getattr(p, "heroes", []) or [])

                heroes = [h for h in heroes_all if _as_int(getattr(h, "time_played", 0)) >= MIN_SECONDS_PLAYED]
                if not heroes:
                    continue

                hero_keys = [
                    f"{_as_text(getattr(h, 'heroname', '')).lower()}:{_as_int(getattr(h, 'time_played', 0))}:{_as_int(getattr(h, 'matches_played', 0))}"
                    for h in heroes
                ]
                hero_keys.sort()

                player_sig = _sha1("|".join([
                    player_name.lower(),
                    season_rank,
                    best_rank,
                    str(is_private),
                    ",".join(hero_keys),
                ]))

                row = cur.execute(
                                    "SELECT player_name, player_sig FROM players WHERE LOWER(player_name)=? LIMIT 1;",
                                    (player_name.lower(),)
                                ).fetchone()
                db_player_name = row["player_name"] if row is not None else player_name
                if row is None:
                    cur.execute("""
                        INSERT INTO players (
                            player_name, first_seen_ts, last_seen_ts,
                            season_rank, best_rank, is_private,
                            player_sig
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (db_player_name, now, now, season_rank, best_rank, is_private, player_sig))

                    ops.append({
                        "ts": now,
                        "table": "players",
                        "op": "insert",
                        "pk": {"player_name": db_player_name},
                        "data": {
                            "first_seen_ts": now,
                            "last_seen_ts": now,
                            "season_rank": season_rank,
                            "best_rank": best_rank,
                            "is_private": is_private,
                            "player_sig": player_sig,
                        }
                    })
                else:
                    old_sig = row["player_sig"]
                    if old_sig != player_sig:
                        cur.execute("""
                            UPDATE players
                            SET last_seen_ts=?, season_rank=?, best_rank=?, is_private=?, player_sig=?
                            WHERE player_name=?;
                        """, (now, season_rank, best_rank, is_private, player_sig, db_player_name))

                        ops.append({
                            "ts": now,
                            "table": "players",
                            "op": "update",
                            "pk": {"player_name": db_player_name},
                            "data": {
                                "last_seen_ts": now,
                                "season_rank": season_rank,
                                "best_rank": best_rank,
                                "is_private": is_private,
                                "player_sig": player_sig,
                            }
                        })
                    else:
                        cur.execute("UPDATE players SET last_seen_ts=? WHERE player_name=?;", (now, db_player_name))
                        # usually not worth logging; uncomment if you want
                        # ops.append({...})

                ov = getattr(p, "full_overview", None)
                if ov is not None and _as_int(getattr(ov, "time_played", 0)) >= MIN_SECONDS_OVERVIEW:
                    op = self._upsert_player_overview(cur, db_player_name, ov, now)
                    if op:
                        ops.append(op)

                for h in heroes:
                    time_pl = _as_int(getattr(h, "time_played", 0))
                    if time_pl < MIN_SECONDS_PLAYED:
                        continue
                    

            
                    op = self._upsert_player_hero(cur, db_player_name, h, now)
                    if op:
                        ops.append(op)
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log.append(f"[{ts}] {db_player_name}: Upserting {getattr(h, 'heroname', '')} with playtime {round(time_pl/3600,1)} hours")
                    else:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log.append(f"[{ts}] {db_player_name}: SKIP: No update needed for {getattr(h, 'heroname', '')} with playtime {round(time_pl/3600,1)} hours")
            timee = datetime.now().toordinal()
            log_path = os.path.join(config.sqlite_db_dir, str(timee) +" " + DEFAULT_LOG)
            save_list_to_log(log, log_path, timestamp=False, mode="a")
        return ops

    def upsert_players2(self, players: Iterable[Any]) -> None:
        """
        Upsert all provided Player objects + their Hero objects.
        Skips DB writes if signatures match existing rows.
        Executes in a single transaction for speed.
        """
        now = _now_ts()
        cur = self.conn.cursor()
        log = []
        with self.conn:  # one transaction
            for p in players:
                player_name = _as_text(getattr(p, "name", "")).strip()
                if not player_name:
                    continue

                


                season_rank = _as_text(getattr(p, "season_rank", ""), "")
                best_rank = _as_text(getattr(p, "best_rank", ""), "")
                is_private = 1 if bool(getattr(p, "bPrivate", False)) else 0
                fo = getattr(p, "full_overview", None)
                if fo is None:
                    heroes_all = getattr(p, "heroes", []) or []
                else:
                    heroes_all = getattr(fo, "heroes", []) or []
                # ---- FILTER HEROES HERE ----
                heroes = [
                    h for h in heroes_all
                    if _as_int(getattr(h, "matches_played", 0)) >= MIN_HERO_MATCHES
                ]

                # If no heroes qualify → SKIP PLAYER ENTIRELY
                if not heroes:
                    continue


                hero_keys = [
                    f"{_as_text(getattr(h, 'heroname', '')).lower()}:{_as_int(getattr(h, 'time_played', 0))}:{_as_int(getattr(h, 'matches_played', 0))}"
                    for h in heroes
                ]
                hero_keys.sort()

                player_sig = _sha1("|".join([
                    player_name.lower(),
                    season_rank,
                    best_rank,
                    str(is_private),
                    ",".join(hero_keys),
                ]))

                row = cur.execute(
                    "SELECT player_sig FROM players WHERE player_name=?;",
                    (player_name,)
                ).fetchone()

                if row is None:
                    cur.execute("""
                        INSERT INTO players (
                            player_name, first_seen_ts, last_seen_ts,
                            season_rank, best_rank, is_private,
                            player_sig
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?);
                    """, (player_name, now, now, season_rank, best_rank, is_private, player_sig))
                else:
                    old_sig = row["player_sig"]
                    if old_sig != player_sig:
                        cur.execute("""
                            UPDATE players
                            SET last_seen_ts=?, season_rank=?, best_rank=?, is_private=?, player_sig=?
                            WHERE player_name=?;
                        """, (now, season_rank, best_rank, is_private, player_sig, player_name))
                    else:
                        cur.execute("UPDATE players SET last_seen_ts=? WHERE player_name=?;", (now, player_name))
                ov = getattr(p, "seasonal_overview", None)
                if ov is not None:
                    # optional: also require overview matches >= threshold
                    if _as_int(getattr(ov, "time_played", 0)) >= MIN_SECONDS_PLAYED:
                        self._upsert_player_overview(cur, player_name, ov, now)
                
                
                for h in heroes:
                    time_pl = _as_int(getattr(h, "time_played", 0))
                    if time_pl < MIN_SECONDS_PLAYED:
                        continue
                    
                    success =  self._upsert_player_hero(cur, player_name, h, now)
                    if success is not None:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log.append(f"[{ts}] {player_name}: Upserting {getattr(h, 'heroname', '')} with playtime {round(time_pl/3600,1)} hours")
                    else:
                        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        log.append(f"[{ts}] {player_name}: SKIP: No update needed for {getattr(h, 'heroname', '')} with playtime {round(time_pl/3600,1)} hours")

            log_path = os.path.join(config.sqlite_db_dir, ts +" " + DEFAULT_LOG)
            save_list_to_log(log, log_path, timestamp=False, mode="a")

    def _upsert_player_hero(self, cur: sqlite3.Cursor, player_name: str, hero_obj: Hero, now: int) -> None:
        hero_name = _as_text(getattr(hero_obj, "heroname", "")).strip()
        
        if not hero_name:
            return

        role = _as_text(getattr(hero_obj, "role", ""), "")

        matches_played = _as_int(getattr(hero_obj, "matches_played", 0))
        matches_won = _as_int(getattr(hero_obj, "matches_won", 0))
        win_pct = _pct_to_float(str(getattr(hero_obj, "win_pct_raw", "0"))+"%")

        time_played = _as_int(getattr(hero_obj, "time_played", 0))
        time_played_won = _as_int(getattr(hero_obj, "time_played_won", 0))

        kills = _as_int(getattr(hero_obj, "kills", 0))
        assists = _as_int(getattr(hero_obj, "assists", 0))
        deaths = _as_int(getattr(hero_obj, "deaths", 0))

        kd_ratio = _as_float(getattr(hero_obj, "kd_ratio", 0.0))
        kda_ratio = _as_float(getattr(hero_obj, "kda_ratio", 0.0))

        total_damage = _as_float(getattr(hero_obj, "total_damage", 0.0))
        total_healing = _as_float(getattr(hero_obj, "total_healing", 0.0))

        damage_per_minute = _as_int(getattr(hero_obj, "damage_per_game_10_raw", 0))
        healing_per_minute = _as_int(getattr(hero_obj, "healing_per_game_10_raw", 0))

        total_damage_taken = _as_float(getattr(hero_obj, "total_damage_taken", 0.0))
        total_damage_taken_per_minute = _as_int(getattr(hero_obj, "total_damage_taken_per_game_10_raw", 0))
        last_kills = _as_int(getattr(hero_obj, "last_kills", 0))
        head_kills = _as_int(getattr(hero_obj, "head_kills", 0))
        average_lifespan = _as_float(getattr(hero_obj, "deaths_per_game_10_raw", 0.0))
        kills_per_10 = _as_float(getattr(hero_obj, "kills_per_game_10_raw", 0.0))
        assists_per_10 = _as_float(getattr(hero_obj, "assists_per_game_10_raw", 0.0))

        total_mvp = _as_int(getattr(hero_obj, "total_mvp", 0))
        total_svp = _as_int(getattr(hero_obj, "total_svp", 0))

        mvp_pct = _pct_to_float(str(getattr(hero_obj, "mvp_pct_raw", "0"))+"%")
        svp_pct = _pct_to_float(str(getattr(hero_obj, "svp_pct_raw", "0"))+"%")

        last_kills_per_10 = _as_float(getattr(hero_obj, "last_kills_per_game_10_raw", 0.0))
        head_kills_per_10 = _as_float(getattr(hero_obj, "head_kills_per_game_10_raw", 0.0))
        # Your Hero object stores these as '47%' strings
        accuracy = _pct_str_to_float(getattr(hero_obj, "accuracy", 0.0))
        headshot_accuracy = _pct_str_to_float(getattr(hero_obj, "headshot_accuracy", 0.0))


        hero_sig = _sha1("|".join(map(str, [
            player_name.lower(), hero_name.lower(), role,
            matches_played, matches_won, win_pct,
            time_played, time_played_won,
            kills, assists, deaths,
            kd_ratio, kda_ratio,
            total_damage, total_healing,
            damage_per_minute, healing_per_minute,
            total_damage_taken, total_damage_taken_per_minute,
            last_kills, head_kills, average_lifespan, kills_per_10, assists_per_10,
            total_mvp, total_svp,
            mvp_pct, svp_pct,
            last_kills_per_10, head_kills_per_10,
            accuracy, headshot_accuracy,
        ])))

        row = cur.execute("""
                    SELECT hero_sig FROM player_heroes
                    WHERE LOWER(player_name)=? AND hero_name=?;
                """, (player_name.lower(), hero_name)).fetchone()
        

        if row is not None and row["hero_sig"] == hero_sig:
            return None  # unchanged

        op_kind = "insert" if row is None else "update"

        cur.execute("""
            INSERT INTO player_heroes (
                player_name, hero_name, role,
                matches_played, matches_won, win_pct,
                time_played, time_played_won,
                kills, assists, deaths,
                kd_ratio, kda_ratio,
                total_damage, total_healing,
                damage_per_minute, healing_per_minute,
                total_damage_taken, total_damage_taken_per_minute,
                last_kills, head_kills, average_lifespan, kills_per_10, assists_per_10,
                total_mvp, total_svp,
                mvp_pct, svp_pct,
                last_kills_per_10, head_kills_per_10, accuracy, headshot_accuracy,
                last_updated_ts, hero_sig
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

            ON CONFLICT(player_name, hero_name) DO UPDATE SET
                role=excluded.role,
                matches_played=excluded.matches_played,
                matches_won=excluded.matches_won,
                win_pct=excluded.win_pct,
                time_played=excluded.time_played,
                time_played_won=excluded.time_played_won,
                kills=excluded.kills,
                assists=excluded.assists,
                deaths=excluded.deaths,
                kd_ratio=excluded.kd_ratio,
                kda_ratio=excluded.kda_ratio,
                total_damage=excluded.total_damage,
                total_healing=excluded.total_healing,
                damage_per_minute=excluded.damage_per_minute,
                healing_per_minute=excluded.healing_per_minute,
                total_damage_taken=excluded.total_damage_taken,
                total_damage_taken_per_minute=excluded.total_damage_taken_per_minute,
                last_kills=excluded.last_kills,
                head_kills=excluded.head_kills,
                average_lifespan=excluded.average_lifespan,
                kills_per_10=excluded.kills_per_10,
                assists_per_10=excluded.assists_per_10,
                total_mvp=excluded.total_mvp,
                total_svp=excluded.total_svp,
                mvp_pct=excluded.mvp_pct,
                svp_pct=excluded.svp_pct,
                last_kills_per_10=excluded.last_kills_per_10,
                head_kills_per_10=excluded.head_kills_per_10,
                accuracy=excluded.accuracy,
                headshot_accuracy=excluded.headshot_accuracy,
                last_updated_ts=excluded.last_updated_ts,
                hero_sig=excluded.hero_sig;
        """, (
            player_name, hero_name, role,
            matches_played, matches_won, win_pct,
            time_played, time_played_won,
            kills, assists, deaths,
            kd_ratio, kda_ratio,
            total_damage, total_healing,
            damage_per_minute, healing_per_minute,
            total_damage_taken, total_damage_taken_per_minute,
            last_kills, head_kills,
            average_lifespan, kills_per_10, assists_per_10,
            total_mvp, total_svp,
            mvp_pct, svp_pct,
            last_kills_per_10, head_kills_per_10, accuracy, headshot_accuracy,
            now, hero_sig
        ))
        return {
        "ts": now,
        "table": "player_heroes",
        "op": op_kind,
        "pk": {"player_name": player_name, "hero_name": hero_name},
        "data": {
            "role": role,
            "matches_played": matches_played,
            "matches_won": matches_won,
            "win_pct": win_pct,
            "time_played": time_played,
            "time_played_won": time_played_won,
            "kills": kills,
            "assists": assists,
            "deaths": deaths,
            "kd_ratio": kd_ratio,
            "kda_ratio": kda_ratio,
            "total_damage": total_damage,
            "total_healing": total_healing,
            "damage_per_minute": damage_per_minute,
            "healing_per_minute": healing_per_minute,
            "total_damage_taken": total_damage_taken,
            "total_damage_taken_per_minute": total_damage_taken_per_minute,
            "last_kills": last_kills,
            "head_kills": head_kills,
            "average_lifespan": average_lifespan,
            "kills_per_10": kills_per_10,
            "assists_per_10": assists_per_10,
            "total_mvp": total_mvp,
            "total_svp": total_svp,
            "mvp_pct": mvp_pct,
            "svp_pct": svp_pct,
            "last_kills_per_10": last_kills_per_10,
            "head_kills_per_10": head_kills_per_10,
            "accuracy": accuracy,
            "headshot_accuracy": headshot_accuracy,
            "last_updated_ts": now,
            "hero_sig": hero_sig,
        }
    }

    # ----------------------------
    # Percentile leaderboard lookup
    # ----------------------------

    def stat_percentile(
        self,
        hero_name: str,
        stat_key: str,
        stat_value: float,
        *,
        direction: Optional[str] = None,
        min_samples: int = 25,
    ) -> Optional[float]:
        """
        Percentile where 0.0 = best, 100.0 = worst for given hero+stat.
        Works even if you haven't inserted the current player yet (you pass stat_value).
        Returns None if insufficient samples.
        """
        hero_name = (hero_name or "").strip()
        stat_key = (stat_key or "").strip()
        stat_value = _pct_to_float(stat_value)

        if not hero_name or not stat_key:
            return None
        if stat_key not in self.ALLOWED_NUMERIC_COLS:
            return None

        direction = direction or self.STAT_DIR.get(stat_key, "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"

        cur = self.conn.cursor()

        total = cur.execute(
            f"SELECT COUNT(*) AS n FROM player_heroes WHERE hero_name=? AND {stat_key} IS NOT NULL;",
            (hero_name,),
        ).fetchone()["n"]

        if total < min_samples:
            return None

        if direction == "desc":  # higher is better
            better = cur.execute(
                f"SELECT COUNT(*) AS n FROM player_heroes WHERE hero_name=? AND {stat_key} > ?;",
                (hero_name, stat_value),
            ).fetchone()["n"]
        else:  # lower is better
            better = cur.execute(
                f"SELECT COUNT(*) AS n FROM player_heroes WHERE hero_name=? AND {stat_key} < ?;",
                (hero_name, stat_value),
            ).fetchone()["n"]

        pct = (better / total) * 100.0
        if pct < 0:
            pct = 0.0
        if pct > 100:
            pct = 100.0
        return round(pct, 2)
    
    def overview_stat_percentile(
        self,
        stat_key: str,
        stat_value: float,
        *,
        direction: Optional[str] = None,
        min_samples: int = 5,
    ) -> Optional[float]:
        """
        Percentile where 0.0 = best, 100.0 = worst for a player_overview stat.
        Works even if you haven't inserted the current player yet (you pass stat_value).
        Returns None if insufficient samples.
        """

        stat_key = (stat_key or "").strip()
        stat_value = _pct_to_float(stat_value)
        if not stat_key:
            return None

        if stat_key not in self.OV_ALLOWED:
            return None

        direction = direction or self.OV_STAT_DIR.get(stat_key, "desc")
        if direction not in ("asc", "desc"):
            direction = "desc"

        cur = self.conn.cursor()

        total = cur.execute(
            f"""
            SELECT COUNT(*) AS n
            FROM player_overview
            WHERE {stat_key} IS NOT NULL;
            """
        ).fetchone()["n"]

        if total < min_samples:
            return None

        if direction == "desc":  # higher is better
            better = cur.execute(
                f"""
                SELECT COUNT(*) AS n
                FROM player_overview
                WHERE {stat_key} > ?;
                """,
                (stat_value,),
            ).fetchone()["n"]
        else:  # lower is better
            better = cur.execute(
                f"""
                SELECT COUNT(*) AS n
                FROM player_overview
                WHERE {stat_key} < ?;
                """,
                (stat_value,),
            ).fetchone()["n"]

        pct = (better / total) * 100.0
        pct = max(0.0, min(100.0, pct))
        return round(pct, 2)

    def get_all_player_names(self):
        cur = self.conn.cursor()
        rows = cur.execute("SELECT player_name FROM players;").fetchall()
        return [row["player_name"] for row in rows]
    
if __name__ == "__main__":
    import shutil
    from datetime import datetime

    src = _db_path()
    if not os.path.exists(src):
        raise SystemExit(f"[SMOKE] Source DB not found: {src}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.splitext(src)[0] + f"_MIGRATION_TEST_{ts}.db"

    # --- Copy DB safely (handles your current WAL setup) ---
    # If WAL files exist, copy them too so the clone is consistent.
    # (If you want *perfect* consistency, close your app before running this.)
    shutil.copy2(src, dst)

    wal_src = src + "-wal"
    shm_src = src + "-shm"
    if os.path.exists(wal_src):
        shutil.copy2(wal_src, dst + "-wal")
    if os.path.exists(shm_src):
        shutil.copy2(shm_src, dst + "-shm")

    print(f"[SMOKE] Copied:\n  from: {src}\n  to:   {dst}")

    # --- Open cloned DB; this will run _init_schema() and apply migrations ---
    db = StatsDB(db_path=dst)

    # --- Verify columns exist ---
    cur = db.conn.cursor()
    cols = {r["name"] for r in cur.execute("PRAGMA table_info(player_heroes);").fetchall()}
    needed = {"last_kills_per_10", "head_kills_per_10", "accuracy", "headshot_accuracy"}

    missing = needed - cols
    if missing:
        print("[SMOKE] ❌ Missing columns:", sorted(missing))
    else:
        print("[SMOKE] ✅ All new columns present:", sorted(needed))

    # Optional: verify indexes exist (not required)
    # idx = [r["name"] for r in cur.execute("PRAGMA index_list(player_heroes);").fetchall()]
    # print("[SMOKE] Indexes:", idx)

    db.close()
    print(f"[SMOKE] Done. Test DB saved at: {dst}")

