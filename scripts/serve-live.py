#!/usr/bin/env python3
"""
Live EPUB-style preview server for editing chapters in the browser.

Install once:
  python3 -m pip install -r scripts/requirements-epub.txt

Run (from anywhere):
  python3 scripts/serve-live.py --open

Open http://127.0.0.1:8765/ — do not use file:// (fetch API needs HTTP).
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import unquote, urlparse

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from book_render import chapter_files, chapter_slug, chapter_title_from_md, read_chapter, repo_root  # noqa: E402


def _json_response(handler: SimpleHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(*, root: Path, chapters_dir: Path):
    allowed: dict[str, Path] = {p.name: p for p in chapter_files(chapters_dir)}

    class LiveHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(root), **kwargs)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            if self.path.startswith("/api/"):
                return
            super().log_message(format, *args)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path

            if path == "/api/manifest":
                chapters = []
                for name, chap_path in sorted(allowed.items()):
                    stat = chap_path.stat()
                    raw = chap_path.read_text(encoding="utf-8")
                    title = chapter_title_from_md(raw, chap_path.stem)
                    chapters.append(
                        {
                            "file": name,
                            "title": title,
                            "mtime": stat.st_mtime,
                            "slug": chapter_slug(chap_path),
                        }
                    )
                _json_response(self, 200, {"chapters": chapters})
                return

            prefix = "/api/chapter/"
            if path.startswith(prefix):
                name = unquote(path[len(prefix) :]).lstrip("/")
                if ".." in name or "/" in name or "\\" in name:
                    _json_response(self, 400, {"error": "invalid chapter name"})
                    return
                chap_path = allowed.get(name)
                if chap_path is None:
                    _json_response(self, 404, {"error": "chapter not found"})
                    return
                file_name, title, html, mtime = read_chapter(chap_path)
                _json_response(
                    self,
                    200,
                    {
                        "file": file_name,
                        "title": title,
                        "mtime": mtime,
                        "slug": chapter_slug(chap_path),
                        "html": html,
                    },
                )
                return

            if path in ("", "/"):
                self.path = "/index.html"
            super().do_GET()

    return LiveHandler


def main() -> None:
    root = repo_root()
    ap = argparse.ArgumentParser(description="Serve live EPUB-style chapter preview.")
    ap.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    ap.add_argument(
        "--chapters-dir",
        type=Path,
        default=root / "chapters",
        help="Directory of chapter .md files",
    )
    ap.add_argument("--open", action="store_true", help="Open the preview in the default browser")
    args = ap.parse_args()

    chapters_dir = args.chapters_dir.resolve()
    if not chapters_dir.is_dir():
        print(f"Not a directory: {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    paths = chapter_files(chapters_dir)
    if not paths:
        print(f"No chapter files matching NN-*.md in {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    handler = make_handler(root=root, chapters_dir=chapters_dir)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    url = f"http://{args.host}:{args.port}/"

    print(f"Serving {len(paths)} chapters at {url}")
    print("Press Ctrl+C to stop.")

    if args.open:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
