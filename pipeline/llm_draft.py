"""LLM draft pipeline: fill in intro via Claude API (optional, MVP not used)."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Optional

from config import FRUITS_JSON
from services.claude import generate_flower_text
from services.wikipedia import get_summary


def run(
    force: bool = False,
    only: Optional[list[str]] = None,
    limit: Optional[int] = None,
) -> int:
    """Generate intro for fruits missing it. Returns count generated.

    Note: MVP fruits-viewer expects intro/varieties/nutrition/storage/prices
    to come from raw/manual_drafts.json (apply-drafts pipeline). This step
    is preserved for future automation but not part of the default pipeline.
    """
    if not FRUITS_JSON.exists():
        print("[llm-draft] fruits.json not found; run `seed` first")
        return 0

    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits = db.get("fruits", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    targets = list(fruits.items())
    if only:
        only_set = set(only)
        targets = [(fid, f) for fid, f in targets if fid in only_set]

    pending = [(fid, f) for fid, f in targets if force or not f.get("intro")]
    if limit:
        pending = pending[:limit]

    print(f"[llm-draft] {len(pending)} fruits to process")

    count = 0
    for i, (fid, f) in enumerate(pending, 1):
        zh_name = (f.get("names") or {}).get("zh") or fid
        sci = (f.get("names") or {}).get("scientific")
        family = f.get("family")
        wiki_title = f.get("wiki_title")
        wiki_extract = ""
        if wiki_title:
            summary = get_summary(wiki_title) or {}
            wiki_extract = summary.get("extract", "")

        print(f"[llm-draft {i}/{len(pending)}] {fid} ({zh_name})")
        result = generate_flower_text(
            zh_name,
            scientific=sci,
            family=family,
            wiki_extract=wiki_extract,
        )
        if not result:
            continue

        # Reuse the result.intro; ignore the "language" (花語) field for fruits.
        f["intro"] = result.get("intro") or f.get("intro")
        f["review_status"] = "draft"
        f["updated_at"] = now
        count += 1

        if count % 5 == 0:
            db["fruits"] = fruits
            FRUITS_JSON.write_text(
                json.dumps(db, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    db["fruits"] = fruits
    db["generated_at"] = now
    FRUITS_JSON.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[llm-draft] generated {count} drafts")
    return count
