"""Anthropic Claude API wrapper for batch flower descriptions."""
from __future__ import annotations
import os
from typing import Optional

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover
    Anthropic = None  # type: ignore

from config import ANTHROPIC_MODEL


def _client() -> "Anthropic":
    if Anthropic is None:
        raise RuntimeError("anthropic package not installed; run `pip install anthropic`")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Set it via:\n"
            "  PowerShell:  $env:ANTHROPIC_API_KEY = '<your-key>'\n"
            "  Bash:        export ANTHROPIC_API_KEY='<your-key>'"
        )
    return Anthropic(api_key=api_key)


def generate_flower_text(
    zh_name: str,
    *,
    scientific: Optional[str] = None,
    family: Optional[str] = None,
    wiki_extract: Optional[str] = None,
    model: str = ANTHROPIC_MODEL,
) -> Optional[dict]:
    """Generate {language: '...', intro: '...'} for one flower.

    `language` = 花語 (a few short phrases, comma-separated, < 30 chars)
    `intro`    = 100-250 字的中文介紹（樸實、避免幻覺；可參考 wiki_extract）
    Returns None on failure.
    """
    client = _client()

    facts = []
    if scientific:
        facts.append(f"學名：{scientific}")
    if family:
        facts.append(f"科：{family}")
    facts_str = "\n".join(facts) if facts else "（無已知事實）"

    wiki_str = wiki_extract.strip() if wiki_extract else "（無維基百科摘要）"

    prompt = f"""你是台灣花卉圖鑑的編輯。請為以下花卉產生繁體中文的「花語」與「介紹」。

花名：{zh_name}
{facts_str}

維基百科摘要（如有）：
{wiki_str}

請輸出 JSON（無其他文字、無 markdown 程式碼框），格式為：
{{
  "language": "花語：3-5 個簡短詞語，以中文逗號分隔，總長度 30 字內",
  "intro": "100-200 字的繁體中文介紹，描述外觀、習性、文化意涵或用途"
}}

注意：
- 不要編造學名、月份、原產地等可驗證的事實
- 介紹要平易近人，適合手機閱讀
- 花語可以浪漫，但不要過於誇張
"""

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[claude] {zh_name} failed: {e}")
        return None

    text = "".join(
        block.text for block in resp.content if hasattr(block, "text")
    ).strip()

    # Extract JSON from response
    import json
    import re
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        print(f"[claude] {zh_name}: could not find JSON in response")
        return None
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        print(f"[claude] {zh_name}: JSON parse error: {e}")
        return None

    lang = (data.get("language") or "").strip()
    intro = (data.get("intro") or "").strip()
    if not lang or not intro:
        return None
    return {"language": lang, "intro": intro}
