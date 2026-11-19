"""SQLite-backed Marvel Rivals proficiency fingerprinting.

Public functions:
    create_fingerprint(player)
    init_fingerprint_db()
    save_fingerprint(fingerprint, fingerprint_id=None)
    load_fingerprint(fingerprint_id)
    compare_fingerprints(live_fingerprint, threshold=85)

Set FINGERPRINT_DB_PATH below to choose the SQLite database location.

A similarity score is a heuristic, NOT a probability of identity. Before
merging records automatically, consider checking for ambiguous matches.
"""

from __future__ import annotations

import math
import sqlite3
import uuid
from pathlib import Path
from typing import Any
import helpers

# -------------------------------- Configuration --------------------------------
FINGERPRINT_DB_PATH = r"PATH_TO_DATABASE.db"  # e.g. r"C:\MyProject\fingerprints.db"
DEFAULT_MATCH_THRESHOLD = 85.0


def _connect() -> sqlite3.Connection:
    path = Path(FINGERPRINT_DB_PATH).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_fingerprint_db() -> None:
    """Create database tables and indexes if they do not exist."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fingerprints (
                id TEXT PRIMARY KEY,
                name TEXT,
                icon TEXT
            );

            CREATE TABLE IF NOT EXISTS proficiency (
                fingerprint_id TEXT NOT NULL,
                hero_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                points INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (fingerprint_id, hero_id),
                FOREIGN KEY (fingerprint_id)
                    REFERENCES fingerprints(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_proficiency_hero_level
                ON proficiency(hero_id, level);
        """)


def create_fingerprint(player: dict[str, Any]) -> dict[str, Any]:
    """Extract icon, all hero proficiency data, and an unmasked name if present.

    The input is a raw player dictionary whose 'proficiency' value is a list.
    """
    if not isinstance(player, dict):
        raise TypeError("player must be a dictionary")

    name = player.get("name")
    icon = player.get("icon")
    result: dict[str, Any] = {
        "icon": str(icon) if icon is not None else None,
        "proficiency": {},
    }

    for hero in player.get("proficiency") or []:
        hero_id = str(int(hero["hero_id"]))
        result["proficiency"][hero_id] = {
            "level": int(hero["level"]),
            "points": int(hero.get("points") or 0),
        }

    if isinstance(name, str) and name and "*" not in name:
        result["name"] = name

    return result


def _normalize_fingerprint(fingerprint: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize fingerprint keys and numeric fields."""
    if not isinstance(fingerprint, dict):
        raise TypeError("fingerprint must be a dictionary")

    heroes = fingerprint.get("proficiency", {})
    if not isinstance(heroes, dict):
        raise TypeError("fingerprint['proficiency'] must be a dictionary")

    normalized: dict[str, Any] = {
        "icon": None if fingerprint.get("icon") is None else str(fingerprint["icon"]),
        "proficiency": {},
    }
    name = fingerprint.get("name")
    if isinstance(name, str) and name and "*" not in name:
        normalized["name"] = name

    for raw_id, data in heroes.items():
        hero_id = str(int(raw_id))
        if not isinstance(data, dict):
            raise TypeError(f"Proficiency for hero {hero_id} must be a dictionary")
        level = int(data["level"])
        points = int(data.get("points") or 0)
        if level < 0 or points < 0:
            raise ValueError(f"Negative proficiency values for hero {hero_id}")
        normalized["proficiency"][hero_id] = {"level": level, "points": points}

    return normalized


def save_fingerprint(
    fingerprint: dict[str, Any], fingerprint_id: str | None = None
) -> str:
    """Insert a fingerprint, or update an existing one by ID.

    Masked/missing names never erase the stored name. When updating an ID,
    existing hero rows are retained and supplied hero rows are upserted.
    Call this only after a reliable identification if reusing an existing ID.
    """
    fp = _normalize_fingerprint(fingerprint)
    if not fp["proficiency"]:
        raise ValueError("Cannot save an empty proficiency fingerprint")

    init_fingerprint_db()
    fingerprint_id = str(fingerprint_id) if fingerprint_id is not None else uuid.uuid4().hex

    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO fingerprints (id, name, icon) VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = COALESCE(excluded.name, fingerprints.name),
                icon = COALESCE(excluded.icon, fingerprints.icon)
            """,
            (fingerprint_id, fp.get("name"), fp["icon"]),
        )
        conn.executemany(
            """
            INSERT INTO proficiency (fingerprint_id, hero_id, level, points)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(fingerprint_id, hero_id) DO UPDATE SET
                level = CASE WHEN excluded.level >= proficiency.level
                             THEN excluded.level ELSE proficiency.level END,
                points = CASE WHEN excluded.level >= proficiency.level
                              THEN excluded.points ELSE proficiency.points END
            """,
            [
                (fingerprint_id, int(hero_id), data["level"], data["points"])
                for hero_id, data in fp["proficiency"].items()
            ],
        )

    return fingerprint_id


def load_fingerprint(fingerprint_id: str) -> dict[str, Any] | None:
    """Load an existing fingerprint by database ID; return None if not found."""
    init_fingerprint_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT name, icon FROM fingerprints WHERE id = ?", (str(fingerprint_id),)
        ).fetchone()
        if row is None:
            return None
        heroes = conn.execute(
            """SELECT hero_id, level, points FROM proficiency
               WHERE fingerprint_id = ?""",
            (str(fingerprint_id),),
        ).fetchall()

    result: dict[str, Any] = {
        "icon": row[1],
        "proficiency": {
            str(hero_id): {"level": level, "points": points}
            for hero_id, level, points in heroes
        },
    }
    if row[0]:
        result["name"] = row[0]
    return result


def _no_match(reason: str) -> dict[str, Any]:
    return {
        "match": False,
        "id": None,
        "name": None,
        "score": 0.0,
        "reason": reason,
        "growth": {},
        "new_heroes": [],
    }


def compare_fingerprints(
    live_fingerprint: dict[str, Any], threshold: float = DEFAULT_MATCH_THRESHOLD
) -> dict[str, Any]:
    """Match the current live fingerprint against all database players.

    Strictly disqualifies each stored candidate if:
      * any stored hero is absent from the live fingerprint, OR
      * any live level is lower than the stored level for the same hero.

    Newly appearing heroes on the live player are allowed. Other growth is
    scored heuristically. Returns the highest-scoring candidate that meets
    'threshold', or a no-match result. The name comes from the DATABASE row.
    """
    live_fp = _normalize_fingerprint(live_fingerprint)
    live = live_fp["proficiency"]
    if not live:
        return _no_match("Live fingerprint contains no proficiency data")
    if not 0 <= threshold <= 100:
        raise ValueError("threshold must be between 0 and 100")

    init_fingerprint_db()

    # Query only eligible DB candidates. SQLite tests BOTH strict exclusions:
    # every DB hero must be present live, and its stored level <= live level.
    # The live data is passed as parameterized SQL values, not string values.
    hero_ids = list(live)
    placeholders = ", ".join("(?, ?)" for _ in hero_ids)
    sql = f"""
        WITH live_heroes(hero_id, level) AS (VALUES {placeholders})
        SELECT f.id, f.name, f.icon, p.hero_id, p.level, p.points
        FROM fingerprints AS f
        JOIN proficiency AS p ON p.fingerprint_id = f.id
        WHERE NOT EXISTS (
            SELECT 1
            FROM proficiency AS db_hero
            LEFT JOIN live_heroes AS lh ON lh.hero_id = db_hero.hero_id
            WHERE db_hero.fingerprint_id = f.id
              AND (lh.hero_id IS NULL OR lh.level < db_hero.level)
        )
        ORDER BY f.id
    """
    args = [value for hero_id in hero_ids for value in (int(hero_id), live[hero_id]["level"])]

    with _connect() as conn:
        rows = conn.execute(sql, args).fetchall()

    # Only compatible candidates are assembled in Python.
    candidates: dict[str, dict[str, Any]] = {}
    for fp_id, name, icon, hero_id, level, points in rows:
        candidate = candidates.setdefault(
            fp_id, {"name": name, "icon": icon, "proficiency": {}}
        )
        candidate["proficiency"][str(hero_id)] = {"level": level, "points": points}

    best = _no_match("No qualifying fingerprint found")
    live_name = live_fp.get("name")
    live_icon = live_fp.get("icon")

    for fp_id, candidate in candidates.items():
        stored = candidate["proficiency"]
        if not stored:
            continue

        growth = {}
        weighted_score = 0.0
        total_weight = 0.0

        for hero_id, old in stored.items():
            new = live[hero_id]
            delta = new["level"] - old["level"]
            growth[hero_id] = delta

            weight = 1.0 + math.log2(1.0 + old["level"])
            similarity = math.exp(-delta / 50.0)

            if delta == 0:
                point_delta = abs(new["points"] - old["points"])
                similarity *= 0.9 + 0.1 * math.exp(-point_delta / 5000.0)

            weighted_score += weight * similarity
            total_weight += weight

        score = 100.0 * weighted_score / total_weight
        db_name = candidate["name"]
        if live_name and db_name:
            if live_name.casefold() == db_name.casefold():
                score += (100.0 - score) * 0.5
            else:
                score *= 0.75  # Names can change.

        db_icon = candidate["icon"]
        if live_icon and db_icon:
            if str(live_icon) == str(db_icon):
                score += (100.0 - score) * 0.15
            else:
                score *= 0.98  # Icons can change.

        score = min(100.0, score)
        if score >= threshold and score > best["score"]:
            best = {
                "match": True,
                "id": fp_id,
                "name": db_name,
                "score": round(score, 2),
                "reason": "Compatible fingerprint",
                "growth": growth,
                "new_heroes": sorted(set(live) - set(stored), key=int),
            }

    return best


if __name__ == "__main__":
    init_fingerprint_db()
    print(f"Fingerprint database initialized: {FINGERPRINT_DB_PATH}")
