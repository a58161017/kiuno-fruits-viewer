"""Seed pipeline: raw/fruits_seed.yaml → data/fruits.json skeleton."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Any

import yaml

from config import FRUITS_JSON, SEED_YAML


def run(force: bool = False) -> int:
    """Build fruits.json skeleton from seed YAML.

    If fruits.json exists, merge: existing entries keep enriched fields
    (intro, varieties, prices, scientific name, etc), only refresh
    seed-controlled fields.
    Returns count of entries written.
    """
    seed = yaml.safe_load(SEED_YAML.read_text(encoding="utf-8"))
    items = seed.get("fruits", [])

    existing: dict[str, Any] = {}
    if FRUITS_JSON.exists() and not force:
        try:
            existing = json.loads(FRUITS_JSON.read_text(encoding="utf-8")).get("fruits", {})
        except Exception:
            existing = {}

    out: dict[str, Any] = {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    seen_ids: set[str] = set()

    for it in items:
        fid = it.get("id")
        if not fid:
            continue
        if fid in seen_ids:
            print(f"[seed] duplicate id skipped: {fid}")
            continue
        seen_ids.add(fid)

        prev = existing.get(fid, {})
        prev_names = prev.get("names", {}) or {}
        prev_cover = prev.get("cover", {}) or {}

        merged = {
            "id": fid,
            "names": {
                "zh": it.get("zh") or prev_names.get("zh", ""),
                "zh_alt": it.get("zh_alt") or prev_names.get("zh_alt", []),
                "en": prev_names.get("en"),
                "scientific": prev_names.get("scientific"),
            },
            "wiki_title": it.get("wiki") or prev.get("wiki_title"),
            "family": prev.get("family"),
            "intro": prev.get("intro"),
            "season_months": it.get("season_months") or prev.get("season_months", []),
            "season_note": prev.get("season_note"),
            "origin_areas": it.get("origin_areas") or prev.get("origin_areas", []),
            "varieties": prev.get("varieties", []),
            "nutrition": prev.get("nutrition", []),
            "storage": prev.get("storage"),
            "prices": prev.get("prices", []),
            "cover": {
                "source_url": prev_cover.get("source_url"),
                "license": prev_cover.get("license"),
                "local": prev_cover.get("local"),
            },
            "review_status": prev.get("review_status", "draft"),
            "updated_at": prev.get("updated_at", now),
        }
        out[fid] = merged

    payload = {
        "version": 1,
        "generated_at": now,
        "fruits": out,
    }
    FRUITS_JSON.parent.mkdir(parents=True, exist_ok=True)
    FRUITS_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[seed] wrote {len(out)} fruits to {FRUITS_JSON}")
    return len(out)
