"""Regenerate every figure: ``python scripts/figures/all.py``."""

from __future__ import annotations

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent

if __name__ == "__main__":
    for script in sorted(HERE.glob("*.py")):
        if script.name in {"all.py", "_svg.py"}:
            continue
        runpy.run_path(str(script), run_name="__main__")
