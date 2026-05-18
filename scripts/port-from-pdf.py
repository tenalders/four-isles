#!/usr/bin/env python3
"""One-time port: extract chapters from the Reedsy PDF into markdown files."""

from __future__ import annotations

import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = ROOT / "202605181930-STANDARD-the-silence-of-songs" / "the-silence-of-songs-STANDARD.pdf"
CHAPTERS = ROOT / "chapters"

# Book page numbers from the PDF contents (1-indexed printed page)
BOOK_STARTS = [
    ("00-prologue.md", "Prologue", 7),
    ("01-the-lost-songs.md", "The Lost Songs", 13),
    ("02-a-knight-and-a-wizard.md", "A Knight and a Wizard", 18),
    ("03-myths-and-legends.md", "Myths & Legends", 25),
    ("04-a-journey-through-the-moors.md", "A Journey Through the Moors", 33),
    ("05-salt-and-stone.md", "Salt & Stone", 39),
    ("06-the-water-horse.md", "The Water Horse", 48),
    ("07-into-the-greatwood.md", "Into the Greatwood", 60),
    ("08-a-bard-takes-flight.md", "A Bard Takes Flight", 69),
    ("09-a-witchs-gifts.md", "A Witch's Gifts", 81),
    ("10-into-the-dark.md", "Into the Dark", 89),
    ("11-the-great-hall.md", "The Great Hall", 101),
    ("12-a-stone-awakens.md", "A Stone Awakens", 108),
]

HEADER_ONLY = {
    "THE SILENCE OF SONGS",
    "PROLOGUE",
    "THE LOST SONGS",
    "A KNIGHT AND A WIZARD",
    "MYTHS & LEGENDS",
    "A JOURNEY THROUGH THE MOORS",
    "SALT & STONE",
    "THE WATER HORSE",
    "INTO THE GREATWOOD",
    "A BARD TAKES FLIGHT",
    "A WITCH'S GIFTS",
    "INTO THE DARK",
    "THE GREAT HALL",
    "A STONE AWAKENS",
}


def book_page_to_pdf_index(book_page: int) -> int:
    """Map printed book page number to 0-based PDF page index."""
    for i in range(fitz.open(PDF).page_count):
        text = fitz.open(PDF)[i].get_text()
        if f"-- {book_page} of" in text or text.strip().endswith(str(book_page)):
            fitz.open(PDF).close()
            return i
    doc = fitz.open(PDF)
    # fallback: contents say prologue starts ~pdf page 7 (index 6)
    idx = max(0, book_page - 1)
    doc.close()
    return idx


def build_page_markers() -> dict[int, int]:
    """Map book page number -> pdf page index via '-- N of 118 --' markers."""
    doc = fitz.open(PDF)
    markers: dict[int, int] = {}
    for i in range(doc.page_count):
        for m in re.finditer(r"-- (\d+) of \d+ --", doc[i].get_text()):
            markers[int(m.group(1))] = i
    doc.close()
    return markers


def extract_page_range(markers: dict[int, int], start_book: int, end_book: int | None) -> str:
    doc = fitz.open(PDF)
    start_pdf = markers.get(start_book, start_book - 1)
    if end_book is None:
        end_pdf = doc.page_count - 1
    else:
        end_pdf = markers.get(end_book, end_book - 1) - 1
        if end_pdf < start_pdf:
            end_pdf = doc.page_count - 1

    chunks: list[str] = []
    for i in range(start_pdf, min(end_pdf + 1, doc.page_count)):
        chunks.append(doc[i].get_text())
    doc.close()
    return "\n".join(chunks)


def text_to_paragraphs(text: str, drop_title: str | None = None) -> list[str]:
    lines = text.splitlines()
    paras: list[str] = []
    buf = ""

    def flush() -> None:
        nonlocal buf
        s = buf.strip()
        if s:
            paras.append(s)
        buf = ""

    skip_next_title = bool(drop_title)

    for raw in lines:
        s = raw.strip()
        if re.match(r"^-- \d+ of \d+ --$", s):
            flush()
            continue
        if s in HEADER_ONLY:
            flush()
            continue
        if re.match(r"^Part One:", s) or s == "I" or s == "Contents":
            flush()
            continue
        if re.match(r"^\d{1,3}$", s):
            flush()
            continue
        if skip_next_title and drop_title and s == drop_title:
            skip_next_title = False
            continue
        if not s:
            flush()
            continue
        if not buf:
            buf = s
        elif buf.endswith("-"):
            buf = buf[:-1] + s
        else:
            buf = buf + " " + s
    flush()

    # drop trailing stray page-number-only paragraphs
    while paras and re.fullmatch(r"\d{1,3}", paras[-1]):
        paras.pop()

    ligatures = {"ﬁ": "fi", "ﬂ": "fl", "ﬀ": "ff", "ﬃ": "ffi", "ﬄ": "ffl"}
    out: list[str] = []
    for p in paras:
        for a, b in ligatures.items():
            p = p.replace(a, b)
        out.append(p)
    return out


def main() -> None:
    if not PDF.is_file():
        raise SystemExit(f"PDF not found: {PDF}")

    markers = build_page_markers()
    CHAPTERS.mkdir(parents=True, exist_ok=True)

    for idx, (fname, title, start_page) in enumerate(BOOK_STARTS):
        end_page = BOOK_STARTS[idx + 1][2] if idx + 1 < len(BOOK_STARTS) else None
        raw = extract_page_range(markers, start_page, end_page)
        paras = text_to_paragraphs(raw, drop_title=title)

        # drop stray chapter number lines at start
        while paras and re.match(r"^\d+$", paras[0]):
            paras.pop(0)
        while paras and paras[0] == title:
            paras.pop(0)

        lines = [f"# {title}", ""]
        for p in paras:
            if p.strip() in ("* * *", "***"):
                lines.extend(["* * *", ""])
            else:
                lines.extend([p, ""])

        out = CHAPTERS / fname
        out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
        print(f"Wrote {out} ({len(paras)} paragraphs)")


if __name__ == "__main__":
    main()
