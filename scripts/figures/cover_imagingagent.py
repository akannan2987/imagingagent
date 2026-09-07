"""Writes docs/img/cover_imagingagent.svg. Edit the SVG text below and rerun."""

from _svg import write_svg

SVG = r"""
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360" font-family="Segoe UI, Helvetica, Arial, sans-serif">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#0f172a"/>
      <stop offset="1" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="360" rx="18" fill="url(#bg)"/>

  <!-- title -->
  <text x="60" y="110" font-size="64" font-weight="700" fill="#f8fafc">ImagingAgent</text>
  <text x="60" y="152" font-size="22" fill="#cbd5e1">One audited imaging pipeline · MRI volumes and pathology slides · agent-operable</text>

  <!-- three pills -->
  <g font-size="18" font-weight="600">
    <rect x="60" y="190" width="230" height="44" rx="22" fill="#5b8def"/>
    <text x="175" y="219" text-anchor="middle" fill="#ffffff">🧠  mri track</text>
    <rect x="310" y="190" width="270" height="44" rx="22" fill="#c2417b"/>
    <text x="445" y="219" text-anchor="middle" fill="#ffffff">🔬  pathology track</text>
    <rect x="600" y="190" width="290" height="44" rx="22" fill="#1a7f37"/>
    <text x="745" y="219" text-anchor="middle" fill="#ffffff">🛡️  shared audit &amp; triage</text>
  </g>

  <!-- tagline -->
  <text x="60" y="290" font-size="20" fill="#94a3b8">Which results can you trust? Review only the cases that need you.</text>
  <text x="60" y="322" font-size="16" fill="#64748b">CPU-first · reproducible · Model Context Protocol · research use only</text>

  <!-- stylised volume (stacked slices) -->
  <g transform="translate(940,70)" opacity="0.95">
    <rect x="0" y="60" width="150" height="90" rx="8" fill="#334155" stroke="#5b8def" stroke-width="3"/>
    <rect x="15" y="40" width="150" height="90" rx="8" fill="#3b4a63" stroke="#5b8def" stroke-width="3"/>
    <rect x="30" y="20" width="150" height="90" rx="8" fill="#475569" stroke="#5b8def" stroke-width="3"/>
    <ellipse cx="105" cy="65" rx="28" ry="18" fill="none" stroke="#fbbf24" stroke-width="3"/>
  </g>
  <!-- stylised slide with nuclei -->
  <g transform="translate(940,200)">
    <rect x="0" y="0" width="200" height="110" rx="8" fill="#fde2ea" stroke="#c2417b" stroke-width="3"/>
    <g fill="#7c3aed" opacity="0.8">
      <circle cx="30" cy="30" r="9"/><circle cx="70" cy="45" r="8"/><circle cx="115" cy="28" r="10"/>
      <circle cx="160" cy="50" r="8"/><circle cx="50" cy="80" r="9"/><circle cx="95" cy="75" r="8"/>
      <circle cx="140" cy="88" r="9"/><circle cx="178" cy="85" r="7"/>
    </g>
    <g fill="none" stroke="#1a7f37" stroke-width="2.5">
      <circle cx="30" cy="30" r="13"/><circle cx="115" cy="28" r="14"/><circle cx="140" cy="88" r="13"/>
    </g>
  </g>
</svg>
"""

if __name__ == "__main__":
    write_svg("cover_imagingagent", SVG)
