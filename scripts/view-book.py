#!/usr/bin/env python3
"""
Build a browser preview of the manuscript at trade-paperback proportions (trim + type).

Default trim: 6 in × 9 in (common US literary paperback). Chapters are split into fixed-height
pages in the browser (one sheet per screen page). Cover: ../cover.png relative to output.

Usage:
  python3 scripts/view-book.py
  python3 scripts/view-book.py --open
  python3 scripts/view-book.py --width-in 5.5 --height-in 8.5 --no-cover

Requires: pip install -r scripts/requirements-view-book.txt
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path


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
            "  python3 -m pip install -r scripts/requirements-view-book.txt",
            file=sys.stderr,
        )
        sys.exit(1)
    return md


def _html_shell(
    body_inner: str,
    *,
    trim_w_in: float,
    trim_h_in: float,
    title: str,
) -> str:
    w = trim_w_in
    h = trim_h_in
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --trim-w: {w}in;
      --trim-h: {h}in;
      --page-pad: 0.72in;
      --body: 11pt;
      --line: 1.38;
      --text: #1a1a1a;
      --paper: #faf8f5;
      --shadow: rgba(0,0,0,0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, "Times New Roman", serif;
      background: #2c2c2c;
      color: var(--text);
      min-height: 100vh;
      overflow-x: hidden;
    }}
    .toolbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.75rem 1.25rem;
      padding: 0.55rem 1rem;
      background: #222;
      color: #e8e6e3;
      font-family: system-ui, -apple-system, sans-serif;
      font-size: 13px;
      border-bottom: 1px solid #111;
    }}
    .toolbar label {{ display: flex; align-items: center; gap: 0.5rem; }}
    .toolbar input[type="range"] {{ width: 140px; }}
    .stage-wrap {{
      display: flex;
      justify-content: center;
      padding: 1.25rem 1rem 3rem;
      overflow-x: auto;
    }}
    #stage {{
      transform-origin: top center;
      transition: transform 0.08s ease-out;
      width: max-content;
      margin-left: auto;
      margin-right: auto;
    }}
    .sheet {{
      width: var(--trim-w);
      margin: 0 auto 1.75rem;
      background: var(--paper);
      box-shadow: 0 4px 24px var(--shadow);
      font-size: var(--body);
      line-height: var(--line);
      text-align: justify;
      hyphens: auto;
      -webkit-hyphens: auto;
    }}
    .sheet.page {{
      height: var(--trim-h);
      min-height: var(--trim-h);
      max-height: var(--trim-h);
      padding: var(--page-pad);
      display: flex;
      flex-direction: column;
    }}
    .page-inner {{
      flex: 1 1 auto;
      min-height: 0;
      overflow: hidden;
    }}
    .sheet.page.page--overflow .page-inner {{
      overflow: visible;
    }}
    .sheet.page.page--overflow {{
      height: auto;
      min-height: var(--trim-h);
      max-height: none;
    }}
    .sheet--cover {{
      height: var(--trim-h);
      min-height: var(--trim-h);
      max-height: var(--trim-h);
      padding: 0;
      display: flex;
      align-items: stretch;
      justify-content: center;
      overflow: hidden;
    }}
    .sheet--cover img {{
      display: block;
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .chapter-wrap {{
      position: relative;
      margin: 0 auto;
    }}
    /* Off-screen so initial blocks get real line measure before pagination moves them */
    .chapter-flow {{
      position: absolute;
      left: -99999px;
      top: 0;
      width: var(--trim-w);
      box-sizing: border-box;
      padding: var(--page-pad);
      font-size: var(--body);
      line-height: var(--line);
      text-align: justify;
      visibility: hidden;
      pointer-events: none;
    }}
    .sheet h1, .page-inner h1 {{
      font-size: 1.05rem;
      font-weight: 600;
      line-height: 1.25;
      margin: 0 0 0.35rem;
      text-align: left;
      hyphens: none;
    }}
    .sheet h1 + p, .page-inner h1 + p {{
      margin-top: 0.15rem;
      font-style: italic;
      opacity: 0.92;
    }}
    .sheet hr, .page-inner hr {{
      border: none;
      border-top: 1px solid #c9c3b8;
      margin: 0.65rem 0 0.85rem;
    }}
    .sheet p, .page-inner p {{ margin: 0 0 0.55em; }}
    .sheet em, .page-inner em {{ letter-spacing: 0.01em; }}
    @media print {{
      body {{ background: white; }}
      .toolbar {{ display: none; }}
      .stage-wrap {{ padding: 0; display: block; }}
      #stage {{ transform: none !important; zoom: 1 !important; }}
      .sheet {{
        box-shadow: none;
        page-break-after: always;
        margin: 0;
        break-after: page;
      }}
      .sheet.page.page--overflow {{
        max-height: none;
      }}
      @page {{ size: {w}in {h}in; margin: 0; }}
    }}
  </style>
</head>
<body>
  <div class="toolbar">
    <span><strong>{title}</strong> · trim {w}×{h} in · body split to fixed-height pages</span>
    <label>Scale <input type="range" id="zoom" min="50" max="160" value="100" /></label>
    <span id="zoom-label">100%</span>
  </div>
  <div class="stage-wrap">
    <div id="stage">
      {body_inner}
    </div>
  </div>
  <script>
    (function () {{
      var EPS = 3;

      function paginateChapter(wrap) {{
        var flow = wrap.querySelector(".chapter-flow");
        if (!flow) return;
        var blocks = [];
        for (var c = flow.firstChild; c; c = c.nextSibling) {{
          if (c.nodeType === 1) blocks.push(c);
        }}
        if (!blocks.length) {{
          flow.remove();
          return;
        }}
        var src = wrap.getAttribute("data-file") || "";
        flow.remove();
        var idx = 0;
        while (idx < blocks.length) {{
          var sheet = document.createElement("section");
          sheet.className = "sheet page";
          sheet.setAttribute("data-chapter", src);
          var inner = document.createElement("div");
          inner.className = "page-inner";
          sheet.appendChild(inner);
          wrap.appendChild(sheet);

          while (idx < blocks.length) {{
            var next = blocks[idx];
            inner.appendChild(next);
            if (inner.scrollHeight > inner.clientHeight + EPS) {{
              inner.removeChild(next);
              break;
            }}
            idx++;
          }}

          if (inner.childNodes.length === 0 && idx < blocks.length) {{
            inner.appendChild(blocks[idx]);
            sheet.classList.add("page--overflow");
            idx++;
          }}
        }}
      }}

      function initPagination() {{
        requestAnimationFrame(function () {{
          requestAnimationFrame(function () {{
            document.querySelectorAll(".chapter-wrap").forEach(paginateChapter);
          }});
        }});
      }}

      if (document.readyState === "loading") {{
        document.addEventListener("DOMContentLoaded", initPagination);
      }} else {{
        initPagination();
      }}

      var z = document.getElementById("zoom");
      var stage = document.getElementById("stage");
      var lab = document.getElementById("zoom-label");
      function applyZoom() {{
        var v = Number(z.value);
        if ("zoom" in stage.style) {{
          stage.style.zoom = v + "%";
          stage.style.transform = "";
        }} else {{
          stage.style.zoom = "";
          stage.style.transform = "scale(" + (v / 100) + ")";
          stage.style.transformOrigin = "top center";
        }}
        lab.textContent = v + "%";
      }}
      z.addEventListener("input", applyZoom);
      applyZoom();
    }})();
  </script>
</body>
</html>
"""


def main() -> None:
    root = _repo_root()
    ap = argparse.ArgumentParser(description="Build paperback-scale HTML preview of the book.")
    ap.add_argument(
        "--chapters-dir",
        type=Path,
        default=root / "chapters",
        help="Directory of chapter .md files (default: ./chapters)",
    )
    ap.add_argument(
        "--cover",
        type=Path,
        default=root / "cover.png",
        help="Cover image path (default: ./cover.png)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=root / "build" / "book-preview.html",
        help="Output HTML path (default: ./build/book-preview.html)",
    )
    ap.add_argument("--width-in", type=float, default=6.0, help="Trim width in inches (default: 6)")
    ap.add_argument("--height-in", type=float, default=9.0, help="Trim height in inches (default: 9)")
    ap.add_argument("--no-cover", action="store_true", help="Omit cover sheet")
    ap.add_argument("--open", action="store_true", help="Open the file in the default browser")
    ap.add_argument("--title", default="The Silence of Songs — preview", help="HTML document title")
    args = ap.parse_args()

    chapters_dir = args.chapters_dir.resolve()
    if not chapters_dir.is_dir():
        print(f"Not a directory: {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    md = _load_markdown_module()
    md_extensions = ["extra", "smarty"]

    pieces: list[str] = []
    if not args.no_cover:
        cover = args.cover.resolve()
        if cover.is_file():
            out_parent = args.out.resolve().parent
            try:
                rel_to_out = Path(os_path_relpath(cover, out_parent))
            except ValueError:
                rel_to_out = Path(cover.name)
            img_src = rel_to_out.as_posix()
            pieces.append(
                f'<section class="sheet sheet--cover" aria-label="Cover"><img src="{img_src}" alt="Book cover" /></section>'
            )
        else:
            print(f"Cover not found (skip): {cover}", file=sys.stderr)

    chapter_paths = _chapter_files(chapters_dir)
    if not chapter_paths:
        print(f"No chapter files matching NN-*.md in {chapters_dir}", file=sys.stderr)
        sys.exit(1)

    for path in chapter_paths:
        raw = path.read_text(encoding="utf-8")
        html = md.markdown(raw, extensions=md_extensions)
        pieces.append(
            f'<section class="chapter-wrap" data-file="{path.name}">'
            f'<div class="chapter-flow">{html}</div></section>'
        )

    out = args.out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    doc = _html_shell(
        "\n".join(pieces),
        trim_w_in=args.width_in,
        trim_h_in=args.height_in,
        title=args.title,
    )
    out.write_text(doc, encoding="utf-8")
    print(f"Wrote {out}")

    if args.open:
        webbrowser.open(out.as_uri())


def os_path_relpath(a: Path, b: Path) -> str:
    import os

    return os.path.relpath(a, b)


if __name__ == "__main__":
    main()
