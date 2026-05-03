"""Enrich pipeline: pull facts from zh.wikipedia (scientific name, family, image)."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from typing import Any, Optional

from config import FRUITS_JSON
from services.wikipedia import (
    extract_infobox,
    filename_from_commons_url,
    first_image_filename,
    get_summary,
    get_wikitext,
    summary_image_url,
)


def _pick(d: dict, *keys: str) -> Optional[str]:
    for k in keys:
        v = d.get(k.lower())
        if v:
            return v
    return None


def _extract_scientific(infobox: dict, summary: dict) -> Optional[str]:
    """Try to find the binomial Latin name."""
    # Direct binomial fields
    sci = _pick(infobox, "binomial", "二名法", "學名", "学名")
    if sci:
        sci = re.sub(r"<[^>]+>", "", sci).strip().split("\n")[0].strip()
        if sci and re.match(r"^[A-Z][a-z]+\s+[a-z]", sci):
            return sci

    # Speciesbox: genus + species fields
    genus = _pick(infobox, "genus", "屬")
    species = _pick(infobox, "species", "種")
    if genus and species:
        # Strip wiki markup, take first word of genus
        genus_clean = re.sub(r"<[^>]+>", "", genus).strip().split()[0]
        species_clean = re.sub(r"<[^>]+>", "", species).strip().split()[0]
        if genus_clean and species_clean:
            return f"{genus_clean} {species_clean}"

    # Genus only (genus-level taxon e.g. 杜鵑花屬)
    if genus and not species:
        genus_clean = re.sub(r"<[^>]+>", "", genus).strip().split()[0]
        if genus_clean and re.match(r"^[A-Z][a-z]+$", genus_clean):
            return genus_clean

    # Fallback: extract italicized Latin from summary extract
    extract = summary.get("extract", "") if summary else ""
    m = re.search(r"\b([A-Z][a-z]+\s+[a-z][a-z\-]+)\b", extract)
    if m:
        return m.group(1)
    return None


def _extract_family(infobox: dict, wikitext: str = "") -> Optional[str]:
    fam = _pick(infobox, "科", "familia", "family")
    if fam:
        fam = re.sub(r"<[^>]+>", "", fam).strip()
        if fam:
            return fam
    # Speciesbox typically omits family (uses display parents) — search wikitext
    # for first standalone 「<X>科」 mention near the start
    head = wikitext[:3000]
    m = re.search(r"([一-鿿]{1,6}科)(?:[，。、)\s])", head)
    if m:
        return m.group(1)
    return None


def _extract_en_name(summary: dict) -> Optional[str]:
    """Look for an English alias hint in the summary description."""
    if not summary:
        return None
    desc = summary.get("description", "")
    if desc and re.search(r"[A-Za-z]", desc):
        return desc.strip()
    return None


def run(force: bool = False, only: Optional[list[str]] = None) -> int:
    """Enrich fruits.json with Wikipedia facts. Returns count enriched."""
    if not FRUITS_JSON.exists():
        print("[enrich] fruits.json not found; run `seed` first")
        return 0

    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits: dict[str, Any] = db.get("fruits", {})
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    targets = list(fruits.items())
    if only:
        only_set = set(only)
        targets = [(fid, f) for fid, f in targets if fid in only_set]

    count = 0
    for i, (fid, f) in enumerate(targets, 1):
        title = f.get("wiki_title")
        if not title:
            continue

        already_enriched = bool(f.get("names", {}).get("scientific")) and bool(f.get("family"))
        if already_enriched and not force:
            continue

        print(f"[enrich {i}/{len(targets)}] {fid} ← {title}")
        summary = get_summary(title) or {}
        wikitext = get_wikitext(title) or ""
        infobox = extract_infobox(wikitext)

        sci = _extract_scientific(infobox, summary)
        fam = _extract_family(infobox, wikitext)
        en = _extract_en_name(summary)

        # Prefer the representative image Wikipedia shows on the article header
        # (originalimage / thumbnail). Fallback to wikitext's first image only
        # if summary has none — that fallback is often a chart/fruit/illustration.
        img_url = summary_image_url(summary)
        img_filename = filename_from_commons_url(img_url) if img_url else None
        if not img_url:
            img_filename = first_image_filename(wikitext)

        names = f.get("names", {}) or {}
        if sci and not names.get("scientific"):
            names["scientific"] = sci
        if en and not names.get("en"):
            names["en"] = en
        f["names"] = names
        if fam and not f.get("family"):
            f["family"] = fam
        # Always refresh image fields so re-running enrich picks up better source
        if img_url:
            f["wiki_image_url"] = img_url
        if img_filename:
            f["wiki_image"] = img_filename
        f["updated_at"] = now
        count += 1

    db["fruits"] = fruits
    db["generated_at"] = now
    FRUITS_JSON.write_text(
        json.dumps(db, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[enrich] enriched {count} entries")
    return count
