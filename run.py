"""kiuno-fruits-viewer CLI entrypoint."""
from __future__ import annotations
import argparse
import http.server
import json
import socket
import socketserver
import sys
from pathlib import Path

# Ensure stdout/stderr handle UTF-8 (Windows cp950 default chokes on non-ASCII)
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from config import FRUITS_JSON, ROOT, SERVE_HOST, SERVE_PORT


def cmd_seed(args: argparse.Namespace) -> int:
    from pipeline import seed
    seed.run(force=args.force)
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    from pipeline import enrich
    enrich.run(force=args.force, only=args.only)
    return 0


def cmd_llm_draft(args: argparse.Namespace) -> int:
    from pipeline import llm_draft
    llm_draft.run(force=args.force, only=args.only, limit=args.limit)
    return 0


def cmd_download(args: argparse.Namespace) -> int:
    from pipeline import download
    download.run(force=args.force, only=args.only)
    return 0


def cmd_apply_drafts(_args: argparse.Namespace) -> int:
    from pipeline import apply_drafts
    apply_drafts.run()
    return 0


def cmd_validate(_args: argparse.Namespace) -> int:
    from pipeline import validate
    return 0 if validate.run() == 0 else 1


def cmd_stats(_args: argparse.Namespace) -> int:
    from datetime import date
    if not FRUITS_JSON.exists():
        print("fruits.json not found")
        return 1
    db = json.loads(FRUITS_JSON.read_text(encoding="utf-8"))
    fruits = db.get("fruits", {})
    total = len(fruits)
    reviewed = sum(1 for f in fruits.values() if f.get("review_status") == "reviewed")
    with_cover = sum(
        1 for f in fruits.values()
        if (f.get("cover") or {}).get("local")
        and (ROOT / (f["cover"]["local"])).exists()
    )
    with_intro = sum(1 for f in fruits.values() if f.get("intro"))
    with_sci = sum(1 for f in fruits.values() if (f.get("names") or {}).get("scientific"))
    with_varieties = sum(1 for f in fruits.values() if f.get("varieties"))
    with_nutrition = sum(1 for f in fruits.values() if f.get("nutrition"))
    with_storage = sum(1 for f in fruits.values() if f.get("storage"))
    with_prices = sum(1 for f in fruits.values() if f.get("prices"))
    month = date.today().month
    in_season = sum(
        1 for f in fruits.values()
        if month in (f.get("season_months") or [])
    )

    def pct(n):
        return f"{n*100//max(total,1):>3d}%"

    print(f"水果總數：       {total}")
    print(f"已審核 reviewed：{reviewed:>4d} ({pct(reviewed)})")
    print(f"有封面圖：       {with_cover:>4d} ({pct(with_cover)})")
    print(f"有介紹文：       {with_intro:>4d} ({pct(with_intro)})")
    print(f"有學名：         {with_sci:>4d} ({pct(with_sci)})")
    print(f"有主要品種：     {with_varieties:>4d} ({pct(with_varieties)})")
    print(f"有營養標示：     {with_nutrition:>4d} ({pct(with_nutrition)})")
    print(f"有保存方式：     {with_storage:>4d} ({pct(with_storage)})")
    print(f"有市場價格：     {with_prices:>4d} ({pct(with_prices)})")
    print(f"當季（{month} 月）： {in_season:>4d} ({pct(in_season)})")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """Static http.server bound to ROOT for local preview / LAN testing."""
    handler = http.server.SimpleHTTPRequestHandler

    class Handler(handler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(ROOT), **kw)

        def log_message(self, fmt, *a):
            sys.stderr.write("[serve] " + fmt % a + "\n")

    host = args.host or SERVE_HOST
    port = args.port or SERVE_PORT

    with socketserver.TCPServer((host, port), Handler) as httpd:
        if host in ("0.0.0.0", "::"):
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                local_ip = "<your-LAN-IP>"
            print(f"Serving on http://{host}:{port}/")
            print(f"  本機開啟：  http://127.0.0.1:{port}/")
            print(f"  手機 LAN： http://{local_ip}:{port}/  (同 WiFi 才連得到)")
        else:
            print(f"Serving on http://{host}:{port}/")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[serve] stopped")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    """Run all stages: seed → enrich → download → apply-drafts → validate."""
    print("=== seed ===")
    cmd_seed(args)
    print("\n=== enrich ===")
    cmd_enrich(args)
    if not args.skip_llm:
        print("\n=== llm-draft ===")
        cmd_llm_draft(args)
    if not args.skip_download:
        print("\n=== download ===")
        cmd_download(args)
    print("\n=== apply-drafts ===")
    cmd_apply_drafts(args)
    print("\n=== validate ===")
    cmd_validate(args)
    print("\n=== stats ===")
    cmd_stats(args)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run.py", description="kiuno-fruits-viewer CLI")
    sp = p.add_subparsers(dest="cmd", required=True)

    s = sp.add_parser("seed", help="raw/fruits_seed.yaml → fruits.json skeleton")
    s.add_argument("--force", action="store_true", help="ignore existing fruits.json")
    s.set_defaults(func=cmd_seed)

    s = sp.add_parser("enrich", help="pull facts from zh.wikipedia (scientific/family/cover)")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only", nargs="*", help="restrict to these fruit ids")
    s.set_defaults(func=cmd_enrich)

    s = sp.add_parser("llm-draft", help="generate intro via Claude API (optional)")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only", nargs="*")
    s.add_argument("--limit", type=int, help="max fruits to process this run")
    s.set_defaults(func=cmd_llm_draft)

    s = sp.add_parser("download", help="download covers from Wikimedia Commons")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only", nargs="*")
    s.set_defaults(func=cmd_download)

    s = sp.add_parser("apply-drafts", help="merge raw/manual_drafts.json (intro/varieties/nutrition/storage/prices) into fruits.json")
    s.set_defaults(func=cmd_apply_drafts)

    s = sp.add_parser("validate", help="check schema + season_months + prices structure")
    s.set_defaults(func=cmd_validate)

    s = sp.add_parser("stats", help="show database statistics")
    s.set_defaults(func=cmd_stats)

    s = sp.add_parser("serve", help="start static http.server")
    s.add_argument("--host", default=None, help=f"default {SERVE_HOST}")
    s.add_argument("--port", type=int, default=None, help=f"default {SERVE_PORT}")
    s.set_defaults(func=cmd_serve)

    s = sp.add_parser("pipeline", help="run all stages: seed → enrich → download → apply-drafts → validate")
    s.add_argument("--force", action="store_true")
    s.add_argument("--only", nargs="*")
    s.add_argument("--limit", type=int)
    s.add_argument("--skip-llm", action="store_true", help="skip llm-draft (avoid API cost)")
    s.add_argument("--skip-download", action="store_true")
    s.set_defaults(func=cmd_pipeline)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
