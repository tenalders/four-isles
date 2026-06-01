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

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from book_render import (  # noqa: E402
    chapter_files,
    chapter_title_from_md,
    read_chapter_css,
    render_markdown,
    repo_root,
)


def main() -> None:
    root = repo_root()
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

    paths = chapter_files(chapters_dir)
    if not paths:
        print(f"No chapter files matching NN-*.md in {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    book = epub.EpubBook()
    identifier = args.uuid.strip() or f"urn:uuid:{uuid.uuid4()}"
    book.set_identifier(identifier)
    book.set_title(args.title)
    book.set_language(args.lang)
    book.add_author(args.author)

    book.add_item(epub.EpubNcx())
    nav = epub.EpubNav()
    book.add_item(nav)

    css_item = epub.EpubItem(
        uid="book_css",
        file_name="text/book.css",
        media_type="text/css",
        content=read_chapter_css(root).encode("utf-8"),
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

    # Load front matter (acknowledgments, etc.) before chapters
    front_matter_docs: list[epub.EpubHtml] = []
    ack_path = chapters_dir / "acknowledgments.md"
    if ack_path.is_file():
        raw = ack_path.read_text(encoding="utf-8")
        fragment = render_markdown(raw)
        title = chapter_title_from_md(raw, "Acknowledgments")
        doc = epub.EpubHtml(
            title=title,
            file_name="text/acknowledgments.xhtml",
            lang=args.lang,
        )
        doc.content = fragment.encode("utf-8")
        doc.add_link(href="book.css", rel="stylesheet", type="text/css")
        book.add_item(doc)
        front_matter_docs.append(doc)

    chapter_docs: list[epub.EpubHtml] = []
    for i, path in enumerate(paths, start=1):
        raw = path.read_text(encoding="utf-8")
        fragment = render_markdown(raw)
        title = chapter_title_from_md(raw, path.stem)
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

    # Build TOC: front matter + chapters
    book.toc = tuple(front_matter_docs + chapter_docs)

    spine: list = []
    if not args.no_cover and args.cover.resolve().is_file():
        spine.append("cover")
    spine.append(nav)
    spine.extend(front_matter_docs)
    spine.extend(chapter_docs)
    book.spine = spine

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    epub.write_epub(str(out), book, {"epub3_pages": False})

    print(f"Wrote {out}")

    with zipfile.ZipFile(out, "r") as zf:
        names = zf.namelist()
        if "mimetype" not in names:
            print("Warning: mimetype missing from EPUB", file=sys.stderr)
        if not any(n.endswith("content.opf") for n in names):
            print("Warning: content.opf missing", file=sys.stderr)


if __name__ == "__main__":
    main()
