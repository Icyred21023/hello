# r2_sync.py
# Cloudflare R2 sync helpers for your StatsDB pipeline.
#
# Requires: pip install boto3
#
# This module supports:
#   REGULAR USERS:
#     - bootstrap local DB from cloud master (checkpoint + working db)
#     - append diffs to local JSONL spool
#     - upload spooled diffs on startup
#
#   ADMIN USER:
#     - download cloud master
#     - download all diffs
#     - apply diffs to master
#     - upload new master
#     - delete processed diffs
#
# IMPORTANT:
# - Your StatsDB.upsert_players() must return "ops" for actual writes,
#   where each op is a dict in one of the supported formats (see _apply_op()).
# - Regular users NEVER upload master db. Only upload diffs.
# - Admin uploads master and deletes diffs.

from __future__ import annotations

import os
import json
import time
import shutil
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Iterable

import boto3


# ----------------------------
# R2 Client (S3-compatible)
# ----------------------------

@dataclass
class R2Client:
    bucket: str
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    region_name: str = "auto"

    def __post_init__(self) -> None:
        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name=self.region_name,
        )

    def download_file(self, key: str, local_path: str) -> None:
        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        self.s3.download_file(self.bucket, key, local_path)

    def upload_file(self, local_path: str, key: str) -> None:
        self.s3.upload_file(local_path, self.bucket, key)

    def list_keys(self, prefix: str) -> List[str]:
        keys: List[str] = []
        token = None
        while True:
            kwargs = {"Bucket": self.bucket, "Prefix": prefix}
            if token:
                kwargs["ContinuationToken"] = token
            resp = self.s3.list_objects_v2(**kwargs)
            for obj in resp.get("Contents", []) or []:
                k = obj.get("Key")
                if k:
                    keys.append(k)
            if resp.get("IsTruncated"):
                token = resp.get("NextContinuationToken")
            else:
                break
        return keys

    def delete_key(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)


# ----------------------------
# Paths / filesystem helpers
# ----------------------------

def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

def _ts() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _copy_sqlite_with_wal(src_db: str, dst_db: str) -> None:
    """
    Safe-ish copy for SQLite WAL mode:
    copies db + optional -wal/-shm if present.
    (For perfect consistency: close writers before copying.)
    """
    _ensure_dir(os.path.dirname(dst_db) or ".")
    shutil.copy2(src_db, dst_db)

    wal_src = src_db + "-wal"
    shm_src = src_db + "-shm"
    if os.path.exists(wal_src):
        shutil.copy2(wal_src, dst_db + "-wal")
    if os.path.exists(shm_src):
        shutil.copy2(shm_src, dst_db + "-shm")

def _atomic_replace(src: str, dst: str) -> None:
    """
    Replace dst with src atomically-ish (Windows-safe pattern).
    """
    _ensure_dir(os.path.dirname(dst) or ".")
    tmp = dst + f".tmp_{_ts()}"
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)


# ----------------------------
# Diff spool (regular users)
# ----------------------------

def append_ops_to_spool(spool_path: str, ops: List[Dict[str, Any]]) -> None:
    """
    Appends ops to a JSONL spool (one JSON object per line).
    """
    if not ops:
        return
    _ensure_dir(os.path.dirname(spool_path) or ".")
    with open(spool_path, "a", encoding="utf-8") as f:
        for op in ops:
            f.write(json.dumps(op, ensure_ascii=False) + "\n")

def _read_jsonl_ops(path: str) -> List[Dict[str, Any]]:
    ops: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                ops.append(obj)
    return ops


def regular_upload_spool_if_present(
    *,
    r2: R2Client,
    diffs_prefix: str,
    spool_path: str,
    client_id: str,
    archive_dir: str,
) -> Optional[str]:
    """
    If spool exists and non-empty:
      - upload it as a new diff object (unique name)
      - move spool to archive
      - return uploaded key
    """
    if not os.path.exists(spool_path):
        return None
    if os.path.getsize(spool_path) <= 0:
        try:
            os.remove(spool_path)
        except Exception:
            pass
        return None

    _ensure_dir(archive_dir)

    key = f"{diffs_prefix}{client_id}_{_ts()}_{os.path.basename(spool_path)}"
    r2.upload_file(spool_path, key)

    archived = os.path.join(archive_dir, f"{client_id}_{_ts()}_spool_uploaded.jsonl")
    try:
        shutil.move(spool_path, archived)
    except Exception:
        # if move fails, at least don't double-upload next run
        try:
            os.remove(spool_path)
        except Exception:
            pass

    return key


# ----------------------------
# Regular user DB bootstrap
# ----------------------------

def regular_bootstrap_local_db(
    *,
    r2: R2Client,
    master_key: str,
    local_working_db: str,
    checkpoints_dir: str,
    checkpoint_name: str = "cloud_checkpoint.db",
    # if cloud != checkpoint, we refresh local_working_db from cloud
) -> Dict[str, Any]:
    """
    Regular user boot:
      - Ensure we have a checkpoint of latest cloud master.
      - If cloud master differs from existing checkpoint -> update checkpoint + refresh local_working_db.
      - If cloud master matches checkpoint:
          - keep local_working_db as-is (so user continues building locally offline-style)
    We compare cloud master to checkpoint by downloading cloud master to temp and comparing file size+hash.
    (We avoid expensive row-by-row compare.)

    Returns summary with what happened.
    """
    _ensure_dir(checkpoints_dir)
    checkpoint_path = os.path.join(checkpoints_dir, checkpoint_name)

    with tempfile.TemporaryDirectory(prefix="r2_bootstrap_") as tmp:
        cloud_tmp = os.path.join(tmp, "cloud_master.db")
        r2.download_file(master_key, cloud_tmp)

        cloud_sig = _file_sig(cloud_tmp)
        checkpoint_sig = _file_sig(checkpoint_path) if os.path.exists(checkpoint_path) else None

        refreshed = False
        if checkpoint_sig != cloud_sig:
            # New cloud master → update checkpoint and refresh working db
            _atomic_replace(cloud_tmp, checkpoint_path)
            _atomic_replace(cloud_tmp, local_working_db)
            refreshed = True
        else:
            # cloud same as checkpoint: keep working db (if missing, seed it)
            if not os.path.exists(local_working_db):
                _atomic_replace(checkpoint_path, local_working_db)

        return {
            "local_working_db": local_working_db,
            "checkpoint_path": checkpoint_path,
            "cloud_changed_vs_checkpoint": bool(checkpoint_sig != cloud_sig),
            "refreshed_working_db_from_cloud": refreshed,
        }

def _file_sig(path: str) -> Optional[Tuple[int, int]]:
    """
    Quick signature: (size_bytes, adler32-ish) for cheap compare.
    Uses zlib.adler32 on chunks.
    """
    if not os.path.exists(path):
        return None
    import zlib
    sz = os.path.getsize(path)
    h = 1
    with open(path, "rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h = zlib.adler32(b, h)
    return (sz, h & 0xFFFFFFFF)


# ----------------------------
# Admin merge: apply diffs to master
# ----------------------------

def _pragma_table_info(conn: sqlite3.Connection, table: str) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table});")
    return cur.fetchall()

def _get_pk_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    info = _pragma_table_info(conn, table)
    pk_sorted = sorted([(int(r["pk"]), r["name"]) for r in info if int(r["pk"] or 0) > 0])
    return [name for _, name in pk_sorted]

def _get_all_columns(conn: sqlite3.Connection, table: str) -> List[str]:
    info = _pragma_table_info(conn, table)
    return [r["name"] for r in info]

def _insert_on_conflict_update(
    conn: sqlite3.Connection,
    table: str,
    row: Dict[str, Any],
    pk_cols: Optional[List[str]] = None,
) -> None:
    cols = _get_all_columns(conn, table)
    use_cols = [c for c in cols if c in row]
    if not use_cols:
        return

    pk_cols = pk_cols or _get_pk_columns(conn, table)
    if not pk_cols:
        placeholders = ", ".join(["?"] * len(use_cols))
        col_list = ", ".join(use_cols)
        values = [row.get(c) for c in use_cols]
        conn.execute(f"INSERT INTO {table} ({col_list}) VALUES ({placeholders});", values)
        return

    update_cols = [c for c in use_cols if c not in pk_cols]
    placeholders = ", ".join(["?"] * len(use_cols))
    col_list = ", ".join(use_cols)
    conflict = ", ".join(pk_cols)
    values = [row.get(c) for c in use_cols]

    if not update_cols:
        conn.execute(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict}) DO NOTHING;",
            values,
        )
        return

    set_clause = ", ".join([f"{c}=excluded.{c}" for c in update_cols])
    sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        f"ON CONFLICT({conflict}) DO UPDATE SET {set_clause};"
    )
    conn.execute(sql, values)

def _apply_op(conn: sqlite3.Connection, op: Dict[str, Any]) -> None:
    """
    Supported op formats:

    1) SQL:
       {"sql": "...", "params": [...]}

    2) UPSERT row:
       {"op":"upsert","table":"player_heroes","row":{...}}
       Optional: "pk": ["player_name","hero_name"]

    3) DELETE row:
       {"op":"delete","table":"player_heroes","where":{...}}
    """
    if not isinstance(op, dict):
        return

    if "sql" in op and isinstance(op["sql"], str):
        params = op.get("params", [])
        if params is None:
            params = []
        if not isinstance(params, (list, tuple)):
            params = [params]
        conn.execute(op["sql"], list(params))
        return

    opname = str(op.get("op", "")).strip().lower()
    table = str(op.get("table", "")).strip()
    if not table:
        return

    if opname in ("upsert", "insert", "update"):
        row = op.get("row") or op.get("data") or {}
        if not isinstance(row, dict):
            return
        pk_override = op.get("pk")
        pk_cols = pk_override if isinstance(pk_override, list) and pk_override else None
        _insert_on_conflict_update(conn, table, row, pk_cols=pk_cols)
        return

    if opname == "delete":
        where = op.get("where") or {}
        if not isinstance(where, dict) or not where:
            return
        cols = list(where.keys())
        placeholders = " AND ".join([f"{c}=?" for c in cols])
        params = [where[c] for c in cols]
        conn.execute(f"DELETE FROM {table} WHERE {placeholders};", params)
        return


def admin_download_and_merge_diffs(
    *,
    r2: R2Client,
    master_key: str,
    local_admin_db_path: str,
    diffs_prefix: str = "diffs/",
    delete_diffs_after_merge: bool = True,
) -> Dict[str, Any]:
    """
    Admin-only:
      - download cloud master
      - download all diffs
      - apply to master (single transaction)
      - upload updated master
      - optionally delete diffs
      - write admin-local copy too
    """
    t0 = time.time()
    _ensure_dir(os.path.dirname(local_admin_db_path) or ".")

    with tempfile.TemporaryDirectory(prefix="r2_admin_merge_") as tmp:
        master_tmp = os.path.join(tmp, "master.db")
        merged_tmp = os.path.join(tmp, "master_merged.db")
        diffs_dir = os.path.join(tmp, "diffs")
        os.makedirs(diffs_dir, exist_ok=True)

        # 1) download master
        r2.download_file(master_key, master_tmp)
        shutil.copy2(master_tmp, merged_tmp)

        # 2) list/download diffs
        diff_keys = [k for k in r2.list_keys(diffs_prefix) if k.lower().endswith((".jsonl", ".json"))]
        diff_keys.sort()
        downloaded: List[Tuple[str, str]] = []
        for k in diff_keys:
            local_path = os.path.join(diffs_dir, os.path.basename(k))
            r2.download_file(k, local_path)
            downloaded.append((k, local_path))

        # 3) apply ops
        conn = sqlite3.connect(merged_tmp)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA temp_store=MEMORY;")

        total_ops = 0
        applied_ops = 0
        failed_ops = 0

        try:
            with conn:
                for _, local_path in downloaded:
                    ops = _read_jsonl_ops(local_path)
                    total_ops += len(ops)
                    for op in ops:
                        try:
                            _apply_op(conn, op)
                            applied_ops += 1
                        except Exception:
                            failed_ops += 1
        finally:
            conn.close()

        # 4) write admin-local
        _atomic_replace(merged_tmp, local_admin_db_path)

        # 5) upload master
        r2.upload_file(merged_tmp, master_key)

        # 6) delete diffs
        deleted = 0
        if delete_diffs_after_merge:
            for k, _ in downloaded:
                r2.delete_key(k)
                deleted += 1

        return {
            "master_key": master_key,
            "local_admin_db_path": local_admin_db_path,
            "diffs_prefix": diffs_prefix,
            "diff_files_found": len(diff_keys),
            "diff_files_deleted": deleted,
            "ops_total": total_ops,
            "ops_applied": applied_ops,
            "ops_failed": failed_ops,
            "elapsed_sec": round(time.time() - t0, 2),
        }
