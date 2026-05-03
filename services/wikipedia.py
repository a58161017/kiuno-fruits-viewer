"""zh.wikipedia helpers: page summary + infobox extraction."""
from __future__ import annotations
import re
from typing import Optional
from urllib.parse import quote

from config import WIKIPEDIA_ZH_API, WIKIPEDIA_ZH_W
from services.http import cached_request


def get_summary(title: str) -> Optional[dict]:
    """Fetch page summary via REST API. Returns dict or None if not found."""
    url = f"{WIKIPEDIA_ZH_API}/page/summary/{quote(title, safe='')}"
    return cached_request(
        "wikipedia", "GET", url,
        headers={"Accept": "application/json; charset=utf-8; profile=\"https://www.mediawiki.org/wiki/Specs/Summary/1.4.2\""},
        cache_key=f"summary|{title}",
    )


def get_wikitext(title: str) -> Optional[str]:
    """Fetch page raw wikitext via Action API. Returns wikitext string or None."""
    data = cached_request(
        "wikipedia", "GET", WIKIPEDIA_ZH_W,
        params={
            "action": "parse",
            "page": title,
            "prop": "wikitext",
            "format": "json",
            "redirects": 1,
        },
        cache_key=f"wikitext|{title}",
    )
    if not data or "parse" not in data:
        return None
    return data["parse"].get("wikitext", {}).get("*")


def extract_infobox(wikitext: str) -> dict[str, str]:
    """Parse the first {{Taxobox / 生物分類表 / Infobox}} from wikitext into a flat dict.

    Returns key→value (raw wikitext-stripped). Empty dict if no infobox found.
    """
    if not wikitext:
        return {}

    # Find the infobox block (matches common biology/general infobox templates)
    pattern = re.compile(
        r"\{\{\s*(?:生物分類表|Taxobox|Automatic[ _]taxobox|Speciesbox|Subspeciesbox|Hybridbox|Infraspeciesbox|物種資訊|物种信息|物種"
        r"|植物資訊|Plant[ _]species|Infobox[^|}\n]*)\s*",
        re.IGNORECASE,
    )
    m = pattern.search(wikitext)
    if not m:
        return {}

    # Walk forward finding the matching }} (handle nested braces)
    start = m.end()
    depth = 2
    i = start
    while i < len(wikitext) and depth > 0:
        if wikitext[i:i+2] == "{{":
            depth += 2
            i += 2
        elif wikitext[i:i+2] == "}}":
            depth -= 2
            i += 2
        else:
            i += 1
    block = wikitext[start:i-2] if depth == 0 else wikitext[start:]

    # Split by | at depth 0 (ignore | inside [[..]] and {{..}})
    fields: dict[str, str] = {}
    parts: list[str] = []
    buf: list[str] = []
    depth_brace = 0
    depth_brack = 0
    for ch in block:
        if ch == "|" and depth_brace == 0 and depth_brack == 0:
            parts.append("".join(buf))
            buf = []
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "[":
            depth_brack += 1
        elif ch == "]":
            depth_brack -= 1
        buf.append(ch)
    parts.append("".join(buf))

    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        key = k.strip().lower()
        val = _strip_wikitext(v.strip())
        if key and val:
            fields[key] = val
    return fields


def _strip_wikitext(s: str) -> str:
    """Best-effort cleanup of wikitext markup → plain text."""
    # Remove HTML comments
    s = re.sub(r"<!--.*?-->", "", s, flags=re.DOTALL)
    # Remove ref tags
    s = re.sub(r"<ref[^>]*>.*?</ref>", "", s, flags=re.DOTALL | re.IGNORECASE)
    s = re.sub(r"<ref[^/]*/>", "", s, flags=re.IGNORECASE)
    # Italic / bold markers
    s = re.sub(r"'''?", "", s)
    # [[link|display]] → display ; [[link]] → link
    s = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", s)
    s = re.sub(r"\[\[([^\]]+)\]\]", r"\1", s)
    # Templates {{...}} → strip (best effort)
    while "{{" in s:
        new = re.sub(r"\{\{[^{}]*\}\}", "", s)
        if new == s:
            break
        s = new
    # External links [http://... display] → display
    s = re.sub(r"\[https?://\S+\s+([^\]]+)\]", r"\1", s)
    s = re.sub(r"\[https?://\S+\]", "", s)
    # HTML tags
    s = re.sub(r"<br\s*/?>", "; ", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip().rstrip(";").strip()


def summary_image_url(summary: dict) -> Optional[str]:
    """Get the representative image URL chosen by Wikipedia for the page summary.

    This is what wiki shows on the article header — typically a clean photo
    of the subject, far better than the wikitext's first image (which is
    often a phylogenetic chart, fruit, or illustration).
    """
    if not summary:
        return None
    orig = summary.get("originalimage") or {}
    if orig.get("source"):
        return orig["source"]
    thumb = summary.get("thumbnail") or {}
    return thumb.get("source") or None


def filename_from_commons_url(url: str) -> Optional[str]:
    """Extract the original filename from a commons upload URL.

    Examples:
      .../commons/thumb/1/18/Pink_Prunus_mume_flowers.jpg/3840px-...jpg
                                ^^^^^^^^^^^^^^^^^^^^^^^^^
      .../commons/3/36/Fleur_de_lotus.jpg
                       ^^^^^^^^^^^^^^^^^^
    """
    if not url:
        return None
    from urllib.parse import unquote
    # /thumb/<a>/<ab>/<filename>/<size>px-<filename>
    m = re.search(r"/commons/thumb/[^/]+/[^/]+/([^/]+)/[^/]+$", url)
    if m:
        return unquote(m.group(1))
    # /commons/<a>/<ab>/<filename>
    m = re.search(r"/commons/[^/]+/[^/]+/([^/]+)$", url)
    if m:
        return unquote(m.group(1))
    return None


def first_image_filename(wikitext: str) -> Optional[str]:
    """Find the first File:/Image: filename referenced in wikitext."""
    if not wikitext:
        return None
    m = re.search(r"\[\[\s*(?:File|Image|檔案|文件|图像|圖像):([^|\]\n]+)", wikitext, re.IGNORECASE)
    if not m:
        return None
    return m.group(1).strip()


def commons_image_url(filename: str) -> Optional[str]:
    """Get the original image URL from Wikimedia Commons via Action API."""
    data = cached_request(
        "commons", "GET", "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json",
        },
        cache_key=f"commons|{filename}",
    )
    if not data:
        return None
    pages = (data.get("query", {}) or {}).get("pages", {})
    for _pid, page in pages.items():
        infos = page.get("imageinfo") or []
        if infos:
            return infos[0].get("url")
    return None


def commons_image_meta(filename: str) -> Optional[dict]:
    """Return {url, license, source_page} for a Commons file, or None."""
    data = cached_request(
        "commons", "GET", "https://commons.wikimedia.org/w/api.php",
        params={
            "action": "query",
            "titles": f"File:{filename}",
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "format": "json",
        },
        cache_key=f"commons-meta|{filename}",
    )
    if not data:
        return None
    pages = (data.get("query", {}) or {}).get("pages", {})
    for _pid, page in pages.items():
        infos = page.get("imageinfo") or []
        if infos:
            info = infos[0]
            ext = info.get("extmetadata", {}) or {}
            license_short = (ext.get("LicenseShortName", {}) or {}).get("value")
            descr = (ext.get("ImageDescription", {}) or {}).get("value")
            return {
                "url": info.get("url"),
                "license": license_short,
                "description": descr,
                "source_page": f"https://commons.wikimedia.org/wiki/File:{quote(filename)}",
            }
    return None
