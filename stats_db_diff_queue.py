import os, json, time
from typing import Any, Iterable, Optional

def append_diff_jsonl(
    *,
    path: str,
    user_id: str,
    cloud_etag_base: str,
    ops: list[dict],
) -> None:
    if not ops:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)

    rec = {
        "v": 1,
        "ts": int(time.time()),
        "user_id": user_id,
        "cloud_etag_base": cloud_etag_base,
        "ops": ops,
    }

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
