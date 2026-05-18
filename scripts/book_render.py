"""Shared chapter discovery, Markdown rendering, and EPUB stylesheet for build scripts."""

from __future__ import annotations

import sys
from pathlib import Path

MD_EXTENSIONS = ["extra", "smarty"]


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def chapter_files(chapters_dir: Path) -> list[Path]:
    files = sorted(chapters_dir.glob("[0-9][0-9]-*.md"))
    return [p for p in files if p.is_file()]


def chapter_css_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / "assets" / "book.css"


def read_chapter_css(root: Path | None = None) -> str:
    path = chapter_css_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"Chapter stylesheet not found: {path}")
    return path.read_text(encoding="utf-8")


def load_markdown_module():
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


def chapter_title_from_md(raw: str, fallback: str) -> str:
    for line in raw.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    return fallback


def render_markdown(raw: str, md_module=None) -> str:
    md = md_module or load_markdown_module()
    return md.markdown(raw, extensions=MD_EXTENSIONS)


def chapter_slug(path: Path) -> str:
    """Stable HTML id from filename (e.g. 00-prologue.md -> chapter-00-prologue)."""
    return f"chapter-{path.stem}"


def read_chapter(path: Path) -> tuple[str, str, str, float]:
    """Return (filename, title, html, mtime)."""
    raw = path.read_text(encoding="utf-8")
    title = chapter_title_from_md(raw, path.stem)
    html = render_markdown(raw)
    mtime = path.stat().st_mtime
    return path.name, title, html, mtime
