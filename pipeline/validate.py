"""Validate fruits.json schema + season_months + prices structure."""
from __future__ import annotations
import json
from typing import Any

from config import FRUITS_JSON, PRICE_REGIONS


REQUIRED_FIELDS = ["id", "names", "season_months", "review_status"]


def run() -> int:
    """Run validation. Returns count of issues found."""
    if not FRUITS_JSON.exists():
        print("[validate] fruits.json not found")
        return 1

    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits: dict[str, Any] = db.get("fruits", {})

    issues = 0
    for fid, f in fruits.items():
        # required fields
        for req in REQUIRED_FIELDS:
            if not f.get(req) and f.get(req) != []:
                if req == "season_months":
                    continue  # empty list is ok
                print(f"[validate] {fid}: missing {req}")
                issues += 1

        # names
        names = f.get("names") or {}
        if not names.get("zh"):
            print(f"[validate] {fid}: names.zh is empty")
            issues += 1

        # season_months range
        months = f.get("season_months") or []
        if not isinstance(months, list):
            print(f"[validate] {fid}: season_months not a list")
            issues += 1
        else:
            for m in months:
                if not isinstance(m, int) or m < 1 or m > 12:
                    print(f"[validate] {fid}: season_months has invalid value {m!r}")
                    issues += 1

        # review_status
        rs = f.get("review_status")
        if rs not in ("draft", "reviewed"):
            print(f"[validate] {fid}: review_status is {rs!r}, expected draft|reviewed")
            issues += 1

        # prices structure
        prices = f.get("prices") or []
        if not isinstance(prices, list):
            print(f"[validate] {fid}: prices not a list")
            issues += 1
        else:
            for i, p in enumerate(prices):
                if not isinstance(p, dict):
                    print(f"[validate] {fid}: prices[{i}] not a dict")
                    issues += 1
                    continue
                region = p.get("region")
                if region not in PRICE_REGIONS:
                    print(f"[validate] {fid}: prices[{i}].region {region!r} not in {PRICE_REGIONS}")
                    issues += 1
                if not p.get("range"):
                    print(f"[validate] {fid}: prices[{i}].range is empty")
                    issues += 1

        # varieties / nutrition must be list of strings if present
        for field in ("varieties", "nutrition"):
            val = f.get(field)
            if val is None or val == []:
                continue
            if not isinstance(val, list) or not all(isinstance(x, str) for x in val):
                print(f"[validate] {fid}: {field} should be list[str]")
                issues += 1

        # cover.local existence (warn only)
        cover = f.get("cover") or {}
        local = cover.get("local")
        if local:
            from config import ROOT
            p = ROOT / local
            if not p.exists():
                print(f"[validate] {fid}: cover.local file missing: {local}")
                issues += 1

    if issues == 0:
        print(f"[validate] OK — {len(fruits)} fruits valid")
    else:
        print(f"[validate] {issues} issue(s) found across {len(fruits)} fruits")
    return issues
