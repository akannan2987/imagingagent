"""Writes docs/img/setup_flow.svg — the once-per-machine setup as a checklist."""

from _svg import write_svg

STEPS = [
    ("1", "Python 3.11", "the interpreter that runs the code"),
    ("2", "Git", "the save-game system for code"),
    ("3", "VS Code", "an editor that understands Python"),
    ("4", "GitHub account", "+ a personal access token"),
    ("5", "Project folder", "clone, or unpack"),
    ("6", ".venv", "a sealed toolbox for this project"),
    ("7", "pip install -e .", "the imagingagent command appears"),
    ("8", "doctor + pytest", "healthy · 53 passed"),
]

boxes = []
x0, y, w, gap = 30, 110, 118, 12
for i, (n, title, sub) in enumerate(STEPS):
    x = x0 + i * (w + gap)
    boxes.append(f"""
  <rect x="{x}" y="{y}" width="{w}" height="120" rx="12" fill="#eef4ff" stroke="#5b8def" stroke-width="2"/>
  <circle cx="{x + 22}" cy="{y + 24}" r="14" fill="#5b8def"/>
  <text x="{x + 22}" y="{y + 29}" text-anchor="middle" font-size="14" font-weight="700" fill="#ffffff">{n}</text>
  <text x="{x + 44}" y="{y + 29}" font-size="13" font-weight="700" fill="#1e293b">{title}</text>
  <text x="{x + 12}" y="{y + 60}" font-size="11" fill="#334155">{sub[:26]}</text>
  <text x="{x + 12}" y="{y + 76}" font-size="11" fill="#334155">{sub[26:52]}</text>
  <text x="{x + 12}" y="{y + 105}" font-size="11" fill="#16a34a">✓ verify before step {int(n) + 1 if n != "8" else "…"}</text>""")
    if i < len(STEPS) - 1:
        boxes.append(
            f'  <line x1="{x + w}" y1="{y + 60}" x2="{x + w + gap}" y2="{y + 60}" stroke="#475569" stroke-width="2"/>'
        )

SVG = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="330" viewBox="0 0 1100 330" font-family="Segoe UI, Helvetica, Arial, sans-serif">
  <rect width="1100" height="330" fill="#ffffff"/>
  <text x="550" y="40" text-anchor="middle" font-size="20" font-weight="700" fill="#0f172a">Setting up your workshop — once per machine</text>
  <text x="550" y="66" text-anchor="middle" font-size="13" fill="#475569">Each step is verified before the next. Windows, macOS and RHEL 8 differ only in steps 1–3; everything from step 5 on is identical.</text>
  {"".join(boxes)}
  <rect x="30" y="255" width="1040" height="52" rx="10" fill="#eefbf1" stroke="#1a7f37"/>
  <text x="50" y="278" font-size="13" font-weight="700" fill="#166534">Every session after that:</text>
  <text x="230" y="278" font-family="Menlo, Consolas, monospace" font-size="12" fill="#0f172a">cd imagingagent → activate .venv → git switch develop &amp;&amp; git pull → work → pytest</text>
  <text x="50" y="298" font-size="12" fill="#166534">Later phases add one line: install that track's requirements file (Step 8b in your setup guide).</text>
</svg>
"""

if __name__ == "__main__":
    write_svg("setup_flow", SVG)
