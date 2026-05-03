"""Download covers from Wikimedia Commons + resize via Pillow."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PIL import Image

from config import COVER_MAX_PX, COVERS_DIR, FRUITS_JSON
from services.http import download_binary
from services.wikipedia import commons_image_meta


def _resize(path: Path, max_px: int = COVER_MAX_PX) -> None:
    try:
        img = Image.open(path)
        img = img.convert("RGB")
        w, h = img.size
        if max(w, h) <= max_px:
            img.save(path, "JPEG", quality=85, optimize=True)
            return
        if w >= h:
            new_w = max_px
            new_h = int(h * (max_px / w))
        else:
            new_h = max_px
            new_w = int(w * (max_px / h))
        img = img.resize((new_w, new_h), Image.LANCZOS)
        img.save(path, "JPEG", quality=85, optimize=True)
    except Exception as e:
        print(f"[download] resize failed for {path.name}: {e}")


def run(force: bool = False, only: Optional[list[str]] = None) -> int:
    """Download covers for fruits that have wiki_image but no local file. Returns count."""
    if not FRUITS_JSON.exists():
        print("[download] fruits.json not found")
        return 0

    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits = db.get("fruits", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    COVERS_DIR.mkdir(parents=True, exist_ok=True)

    targets = list(fruits.items())
    if only:
        only_set = set(only)
        targets = [(fid, f) for fid, f in targets if fid in only_set]

    count = 0
    for i, (fid, f) in enumerate(targets, 1):
        cover = f.get("cover") or {}
        local_rel = cover.get("local")
        local_path = COVERS_DIR / f"fruit-{fid}.jpg"

        if local_path.exists() and not force:
            # Already downloaded; ensure metadata path is set
            f["cover"] = {
                **cover,
                "local": f"data/covers/fruit-{fid}.jpg",
            }
            continue

        wiki_image = f.get("wiki_image")
        wiki_image_url = f.get("wiki_image_url")
        if not wiki_image and not wiki_image_url:
            print(f"[download {i}/{len(targets)}] {fid}: no wiki_image, skip")
            continue

        # Prefer the direct upload.wikimedia.org URL (from summary endpoint)
        url: Optional[str] = wiki_image_url
        meta = None
        if not url and wiki_image:
            meta = commons_image_meta(wiki_image)
            if meta:
                url = meta.get("url")
        if not url:
            print(f"[download {i}/{len(targets)}] {fid}: commons lookup failed for {wiki_image}")
            continue

        # Fetch license metadata from Commons using filename (cheap, cached)
        if not meta and wiki_image:
            meta = commons_image_meta(wiki_image)

        print(f"[download {i}/{len(targets)}] {fid} ← {wiki_image or url}")
        ok = download_binary("commons", url, local_path, overwrite=force)
        if not ok:
            continue
        _resize(local_path)

        f["cover"] = {
            "source_url": (meta.get("source_page") if meta else None) or url,
            "license": meta.get("license") if meta else None,
            "local": f"data/covers/fruit-{fid}.jpg",
        }
        f["updated_at"] = now
        count += 1

    db["fruits"] = fruits
    db["generated_at"] = now
    FRUITS_JSON.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[download] downloaded {count} covers")
    return count
