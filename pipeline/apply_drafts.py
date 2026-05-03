"""Apply manually-authored drafts from raw/manual_drafts.json into fruits.json.

Each draft entry can include:
  - intro:      string (100-250 字 繁中介紹)
  - varieties:  string[] (主要品種，例：["愛文", "金煌"])
  - nutrition:  string[] (營養 chips，例：["維生素 C", "膳食纖維"])
  - storage:    string (保存方式說明)
  - prices:     [{region, range, note?}] (region ∈ 北部/中部/南部/東部)
  - season_note: string (產季補充)
  - _status:    "draft"|"reviewed" (override)，預設 reviewed
"""
from __future__ import annotations
import json
from datetime import datetime, timezone

from config import FRUITS_JSON, RAW


MANUAL_DRAFTS = RAW / "manual_drafts.json"


def run() -> int:
    if not MANUAL_DRAFTS.exists():
        print(f"[apply-drafts] {MANUAL_DRAFTS} not found")
        return 0
    if not FRUITS_JSON.exists():
        print("[apply-drafts] fruits.json not found; run `seed` first")
        return 0

    drafts = json.loads(MANUAL_DRAFTS.read_text(encoding="utf-8"))
    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits = db.get("fruits", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    applied = 0
    missing = []
    for fid, payload in drafts.items():
        if fid.startswith("_"):
            continue
        if fid not in fruits:
            missing.append(fid)
            continue
        f = fruits[fid]

        intro = (payload.get("intro") or "").strip()
        varieties = payload.get("varieties") or []
        nutrition = payload.get("nutrition") or []
        storage = (payload.get("storage") or "").strip()
        prices = payload.get("prices") or []
        season_note = (payload.get("season_note") or "").strip()

        if intro:
            f["intro"] = intro
        if varieties:
            f["varieties"] = varieties
        if nutrition:
            f["nutrition"] = nutrition
        if storage:
            f["storage"] = storage
        if prices:
            f["prices"] = prices
        if season_note:
            f["season_note"] = season_note

        # Drafts in manual_drafts.json are considered hand-reviewed by default.
        f["review_status"] = payload.get("_status", "reviewed")
        f["updated_at"] = now
        applied += 1

    db["fruits"] = fruits
    db["generated_at"] = now
    FRUITS_JSON.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[apply-drafts] applied {applied} drafts to fruits.json")
    if missing:
        print(f"[apply-drafts] {len(missing)} ids in drafts but not in fruits.json: {missing}")
    return applied
