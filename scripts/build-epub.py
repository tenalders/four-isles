#!/usr/bin/env python3
"""
Assemble Markdown chapters into an EPUB (same discovery and Markdown extensions as view-book.py).

Install dependencies once:
  python3 -m pip install -r scripts/requirements-epub.txt

Build:
  python3 scripts/build-epub.py

Open the resulting ``build/the-silence-of-songs.epub`` in Apple Books, Calibre, KOReader, etc. No server required.

Requires: ``markdown`` (extra + smarty) and ``ebooklib``.
"""

from __future__ import annotations

import argparse
import sys
import uuid
import zipfile
from pathlib import Path

from ebooklib import epub


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _chapter_files(chapters_dir: Path) -> list[Path]:
    files = sorted(chapters_dir.glob("[0-9][0-9]-*.md"))
    return [p for p in files if p.is_file()]


def _load_markdown_module():
    try:
        import markdown as md  # type: ignore
    except ImportError:
        print(
            "Missing dependency: markdown\n"
            "Install with:\n"
            "  python3 -m pip install -r scripts/requirements-epub.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    return md


def _chapter_title_from_md(raw: str, fallback: str) -> str:
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return fallback


def _chapter_css() -> str:
    return """@namespace epub "http://www.idpf.org/2007/ops";
body {
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif;
  line-height: 1.38;
  margin: 0.5em 0.6em;
  text-align: justify;
  hyphens: auto;
  -epub-hyphens: auto;
}
h1 {
  text-align: left;
  font-size: 1.1em;
  font-weight: 600;
  margin: 0 0 0.4em;
}
h1 + p {
  font-style: italic;
  opacity: 0.95;
  margin-top: 0.1em;
}
p { margin: 0 0 0.55em; }
hr {
  border: none;
  border-top: 1px solid #999;
  margin: 0.7em 0;
}
em { font-style: italic; }
"""


def main() -> None:
    root = _repo_root()
    ap = argparse.ArgumentParser(description="Build an EPUB from Markdown chapters.")
    ap.add_argument("--title", default="The Silence of Songs", help="Book title (DC:title)")
    ap.add_argument("--author", default="Philip Wahl", help="Author (DC:creator)")
    ap.add_argument("--lang", default="en", help="Language code (default: en)")
    ap.add_argument(
        "--chapters-dir",
        type=Path,
        default=root / "chapters",
        help="Directory of chapter .md files",
    )
    ap.add_argument("--cover", type=Path, default=root / "cover.png", help="Cover image path")
    ap.add_argument(
        "--out",
        type=Path,
        default=root / "build" / "the-silence-of-songs.epub",
        help="Output .epub path",
    )
    ap.add_argument(
        "--uuid",
        default="",
        help="Package identifier (default: new urn:uuid:… each build)",
    )
    ap.add_argument("--no-cover", action="store_true", help="Do not embed cover image or cover page")
    args = ap.parse_args()

    chapters_dir = args.chapters_dir.resolve()
    if not chapters_dir.is_dir():
        print(f"Not a directory: {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    paths = _chapter_files(chapters_dir)
    if not paths:
        print(f"No chapter files matching NN-*.md in {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    md = _load_markdown_module()
    md_extensions = ["extra", "smarty"]

    book = epub.EpubBook()
    identifier = args.uuid.strip() or f"urn:uuid:{uuid.uuid4()}"
    book.set_identifier(identifier)
    book.set_title(args.title)
    book.set_language(args.lang)
    book.add_author(args.author)

    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    book.add_item(nav)

    # Same EPUB directory as chapters so stylesheet href is a simple relative name.
    css_item = epub.EpubItem(
        uid="book_css",
        file_name="text/book.css",
        media_type="text/css",
        content=_chapter_css().encode("utf-8"),
    )
    book.add_item(css_item)

    if not args.no_cover:
        cover_path = args.cover.resolve()
        if cover_path.is_file():
            cover_bytes = cover_path.read_bytes()
            cover_name = f"images/{cover_path.name}"
            book.set_cover(cover_name, cover_bytes, create_page=True)
        else:
            print(f"Cover not found (continuing without): {cover_path}", file=sys.stderr)

    chapter_docs: list[epub.EpubHtml] = []
    for i, path in enumerate(paths, start=1):
        raw = path.read_text(encoding="utf-8")
        fragment = md.markdown(raw, extensions=md_extensions)
        title = _chapter_title_from_md(raw, path.stem)
        fname = f"text/chapter-{i:02d}.xhtml"
        doc = epub.EpubHtml(
            title=title,
            file_name=fname,
            lang=args.lang,
        )
        doc.content = fragment.encode("utf-8")
        doc.add_link(href="book.css", rel="stylesheet", type="text/css")
        book.add_item(doc)
        chapter_docs.append(doc)

    book.toc = tuple(chapter_docs)

    spine: list = []
    if not args.no_cover and args.cover.resolve().is_file():
        spine.append("cover")
    spine.append(nav)
    spine.extend(chapter_docs)
    book.spine = spine

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Disable auto page-list (parses every document); cover body can be empty and breaks lxml.
    epub.write_epub(str(out), book, {"epub3_pages": False})

    print(f"Wrote {out}")

    # Smoke check: valid ZIP and required entries
    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
        if "mimetype" not in names:
            print("Warning: mimetype missing from EPUB", file=sys.stderr)
        if not any(n.endswith("content.opf") for n in names):
            print("Warning: content.opf missing", file=sys.stderr)


if __name__ == "__main__":
    main()
