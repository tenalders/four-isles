#!/usr/bin/env python3
"""Reformat chapter markdown to house style: one paragraph per source line.

Heals PDF port damage (one sentence per line, mid-sentence page breaks) and
splits dialogue turns into separate paragraphs. See OUTLINE.md house style.

Usage:
  python3 scripts/split-paragraphs.py              # all NN-*.md in chapters/
  python3 scripts/split-paragraphs.py chapters/01-the-lost-songs.md ...
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHAPTERS = Path(__file__).resolve().parent.parent / "chapters"

SCENE_BREAK = "* * *"

# Dialogue tags: do not start a new paragraph before the next quote
DIALOGUE_TAG = (
    r"(?:said|asked|replied|whispered|called|barked|shouted|cried|murmured|"
    r"added|continued|finished|agreed|ordered|warned|explained|corrected|"
    r"breathed|reported|muttered|admitted|promised|interrupted|suggested|"
    r"demanded|insisted|growled|chimed|croaked|announced|declared|echoed)"
)

# Known PDF running headers (strip if they appear as standalone lines)
STRIP_HEADERS = frozenset(
    {
        "A WITCH'S GIFTS",
        "A WITCHS GIFTS",
        "THE WATER HORSE",
    }
)


def normalize_quotes(text: str) -> str:
    return (
        text.replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2018", "'")
        .replace("\u2019", "'")
    )


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def count_sentences(paragraph: str) -> int:
    return len(re.findall(r"[.!?](?:\s|$)", paragraph))


def ends_with_dialogue_tag(paragraph: str) -> bool:
    return bool(re.search(DIALOGUE_TAG + r"\.\s*$", paragraph.rstrip()))


def _dialogue_split_positions(text: str) -> list[int]:
    """Indices to split *before* (start of new paragraph)."""
    positions: list[int] = []

    # Narration … . "Dialogue"
    for m in re.finditer(r'(?<=[.!?])\s+"', text):
        prefix = text[: m.start()].rstrip()
        if prefix and ends_with_dialogue_tag(prefix):
            continue
        positions.append(m.start())

    # End of one quote, start of another: …?" "Next…
    for m in re.finditer(r'(?<=[.!?]")\s+(?=")', text):
        positions.append(m.start())

    positions = sorted(set(positions))
    return positions


def split_before_dialogue(text: str) -> list[str]:
    """Split before opening quotes that start a new dialogue turn."""
    if not text:
        return []

    positions = _dialogue_split_positions(text)
    if not positions:
        return [text.strip()] if text.strip() else []

    parts: list[str] = []
    start = 0
    for split_at in positions:
        chunk = text[start:split_at].strip()
        if chunk:
            parts.append(chunk)
        start = split_at
        while start < len(text) and text[start].isspace():
            start += 1

    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _is_dialogue_attribution_after_quote(text: str, pos: int) -> bool:
    """True if text after closing quote is 'Alder asked…' not new narration."""
    rest = text[pos:].lstrip()
    return bool(
        re.match(
            r"(?:" + DIALOGUE_TAG + r"|[\w']+(?:\s+[\w']+){0,2}\s+" + DIALOGUE_TAG + r")",
            rest,
        )
    )


def split_after_dialogue_into_narration(text: str) -> list[str]:
    """Split when narration resumes after a closing quote (…" She walked)."""
    parts: list[str] = []
    start = 0
    for m in re.finditer(r'(?<=[.!?]")\s+(?=[A-Z])', text):
        if _is_dialogue_attribution_after_quote(text, m.end() - 1):
            continue
        split_at = m.start() + 1  # after closing quote
        chunk = text[start:split_at].strip()
        if chunk:
            parts.append(chunk)
        start = m.end() - 1  # at capital letter
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts if parts else ([text.strip()] if text.strip() else [])


def merge_orphan_dialogue_tags(paragraphs: list[str]) -> list[str]:
    """Rejoin 'Alder asked…' paragraphs split from the preceding quote."""
    if not paragraphs:
        return paragraphs
    merged: list[str] = [paragraphs[0]]
    tag_only = re.compile(
        r"^[\w']+(?:\s+[\w']+){0,2}\s+" + DIALOGUE_TAG + r"(?:\s|,|$)"
    )
    for p in paragraphs[1:]:
        prev = merged[-1]
        if prev.endswith('"') and tag_only.match(p):
            merged[-1] = prev + " " + p
        else:
            merged.append(p)
    return merged


def split_long_narration(text: str, min_sentences: int = 3, min_chars: int = 400) -> list[str]:
    """Break very long narration-only blocks at sentence boundaries."""
    if '"' in text:
        return [text]
    if len(text) < min_chars and count_sentences(text) < min_sentences + 1:
        return [text]

    parts: list[str] = []
    start = 0
    sentence_ends = list(re.finditer(r'(?<=[.!?])\s+(?=[A-Z])', text))
    if not sentence_ends:
        return [text]

    chunk_start = 0
    chunk_sentences = 0
    for m in sentence_ends:
        chunk_sentences += 1
        chunk_len = m.end() - chunk_start
        if chunk_sentences >= min_sentences and chunk_len >= min_chars:
            parts.append(text[chunk_start : m.start() + 1].strip())
            chunk_start = m.end() - 1
            chunk_sentences = 0

    tail = text[chunk_start:].strip()
    if tail:
        if parts and len(tail) < 120 and count_sentences(tail) <= 1:
            parts[-1] = parts[-1] + " " + tail
        else:
            parts.append(tail)

    return parts if parts else [text]


def split_into_paragraphs(text: str) -> list[str]:
    text = normalize_whitespace(normalize_quotes(text))
    if not text:
        return []

    paragraphs: list[str] = []
    for chunk in split_before_dialogue(text):
        for sub in split_after_dialogue_into_narration(chunk):
            for para in split_long_narration(sub):
                para = para.strip()
                if para:
                    paragraphs.append(para)

    return merge_orphan_dialogue_tags(paragraphs)


def is_strip_header(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    norm = re.sub(r"\s+", " ", s.upper())
    if norm in STRIP_HEADERS:
        return True
    if (
        len(s) < 60
        and s.upper() == s
        and re.search(r"[A-Z]{3,}", s)
        and len(s.split()) >= 2
        and not s.startswith("#")
    ):
        return True
    return False


def process_section(lines: list[str]) -> list[str]:
    """Join a section's lines and reformat into paragraphs."""
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if is_strip_header(s):
            continue
        if re.match(r"^Chapter \d+:\s*.+", s, re.I):
            continue
        if re.match(r"^A Witch'?s Gifts\s*$", s, re.I):
            continue
        cleaned.append(s)

    if not cleaned:
        return []

    blob = normalize_whitespace(" ".join(cleaned))
    return split_into_paragraphs(blob)


def process_file(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith("# "):
            out.append(line)
            out.append("")
            i += 1
            continue

        if line.strip() == SCENE_BREAK:
            if out and out[-1] != "":
                out.append("")
            out.append(SCENE_BREAK)
            out.append("")
            i += 1
            continue

        # Collect until next scene break or EOF (ignore blank lines when joining)
        section_lines: list[str] = []
        while i < len(lines):
            if lines[i].strip() == SCENE_BREAK:
                break
            if lines[i].startswith("# "):
                break
            section_lines.append(lines[i])
            i += 1

        for para in process_section(section_lines):
            out.append(para)
            out.append("")

    while out and out[-1] == "":
        out.pop()
    out.append("")

    path.write_text("\n".join(out), encoding="utf-8")
    print(f"Reformatted {path.name} ({len([l for l in out if l.strip() and l != SCENE_BREAK])} paragraphs)")


def main() -> None:
    if len(sys.argv) > 1:
        files = [Path(p) for p in sys.argv[1:]]
    else:
        # Default: ported chapters only (13–15 are hand-formatted)
        files = sorted(
            p
            for p in CHAPTERS.glob("[0-9][0-9]-*.md")
            if int(p.name[:2]) <= 12
        )

    for f in files:
        if not f.is_file():
            print(f"Skip (not found): {f}", file=sys.stderr)
            continue
        process_file(f)


if __name__ == "__main__":
    main()
