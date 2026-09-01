import os, json, time, uuid, shutil, hashlib
from dataclasses import dataclass
from typing import Optional

import boto3
from botocore.config import Config


@dataclass
class CloudMasterInfo:
    etag: str
    size: int


class R2Client:
    def __init__(self):
        self.endpoint = os.environ["R2_ENDPOINT"]
        self.bucket = os.environ["R2_BUCKET"]
        self.user_prefix = os.environ.get("R2_USER_PREFIX", "users/unknown")

        self.s3 = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )

    def head_master(self, key="db/master.db") -> CloudMasterInfo:
        r = self.s3.head_object(Bucket=self.bucket, Key=key)
        return CloudMasterInfo(etag=r["ETag"], size=r["ContentLength"])

    def download_master(self, dst_path: str, key="db/master.db") -> None:
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        self.s3.download_file(self.bucket, key, dst_path)

    def upload_diff_file(self, local_path: str) -> str:
        ts = time.strftime("%Y%m%d_%H%M%S")
        name = f"{ts}_{uuid.uuid4().hex}.jsonl"
        key = f"diffs/{self.user_prefix}/{name}".replace("//", "/")
        self.s3.upload_file(local_path, self.bucket, key)
        return key


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: str) -> Optional[dict]:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def ensure_cloud_checkpoint_and_working_db(
    *,
    r2: R2Client,
    working_db_path: str,                 # your current config.sqlite_db_path
    checkpoint_dir: str,                  # e.g. <db_dir>/cloud_checkpoint
    master_key: str = "db/master.db",
) -> CloudMasterInfo:
    os.makedirs(os.path.dirname(working_db_path), exist_ok=True)
    os.makedirs(checkpoint_dir, exist_ok=True)

    meta_path = os.path.join(checkpoint_dir, "checkpoint_meta.json")
    checkpoint_db = os.path.join(checkpoint_dir, "checkpoint_master.db")

    cloud = r2.head_master(master_key)
    meta = read_json(meta_path) or {}
    local_etag = meta.get("etag")

    if local_etag == cloud.etag and os.path.exists(checkpoint_db):
        # Cloud unchanged vs checkpoint -> keep working DB as-is
        return cloud

    # Cloud changed (or no checkpoint yet): refresh checkpoint
    r2.download_master(checkpoint_db, master_key)
    write_json(meta_path, {
        "etag": cloud.etag,
        "downloaded_ts": int(time.time()),
        "checkpoint_sha256": file_sha256(checkpoint_db),
    })

    # Reset working DB from checkpoint (overwrite working DB)
    shutil.copy2(checkpoint_db, working_db_path)

    # If you run WAL mode, clear any stale WAL/SHM next to working file
    for suf in ("-wal", "-shm"):
        p = working_db_path + suf
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    return cloud


def upload_pending_diffs_if_any(
    *,
    r2: R2Client,
    pending_jsonl_path: str,
) -> Optional[str]:
    if not os.path.exists(pending_jsonl_path):
        return None
    if os.path.getsize(pending_jsonl_path) <= 0:
        return None

    key = r2.upload_diff_file(pending_jsonl_path)

    # rotate/clear after successful upload
    os.remove(pending_jsonl_path)
    return key
