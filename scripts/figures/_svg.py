"""Tiny shared helper for the figure scripts: write an SVG string to docs/img.

Kept deliberately minimal (no drawing library) so a reader can open any
figure script and see plain SVG text — the same text a browser renders.
"""

from __future__ import annotations

from pathlib import Path

IMG_DIR = Path(__file__).resolve().parents[2] / "docs" / "img"


def write_svg(name: str, svg: str) -> Path:
    """Write ``svg`` to ``docs/img/<name>.svg`` with LF newlines and return the path."""
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    out = IMG_DIR / f"{name}.svg"
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(svg.strip() + "\n")
    print(f"wrote {out.relative_to(IMG_DIR.parents[1])}")
    return out
