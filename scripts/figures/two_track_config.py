"""Writes docs/img/two_track_config.svg — how one config drives two tracks."""

from _svg import write_svg

SVG = r"""
<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="400" viewBox="0 0 1100 400" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="13">
  <defs>
    <marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#475569"/></marker>
  </defs>
  <rect width="1100" height="400" fill="#ffffff"/>
  <text x="550" y="34" text-anchor="middle" font-size="20" font-weight="700" fill="#0f172a">One configuration, two tracks, one contract</text>

  <!-- config file -->
  <rect x="30" y="70" width="300" height="290" rx="12" fill="#f1f5f9" stroke="#94a3b8" stroke-width="2"/>
  <text x="50" y="95" font-weight="700" fill="#334155">configs/default.yaml</text>
  <g font-family="Menlo, Consolas, monospace" font-size="12" fill="#0f172a">
    <text x="50" y="120">paths: …</text>
    <text x="50" y="142" fill="#2f5bb7">tracks:</text>
    <text x="50" y="162" fill="#2f5bb7">  mri:</text>
    <text x="50" y="180" fill="#2f5bb7">    enabled: true</text>
    <text x="50" y="198" fill="#2f5bb7">    dataset: msd_task04…</text>
    <text x="50" y="216" fill="#2f5bb7">    target_spacing_mm: [1,1,1]</text>
    <text x="50" y="238" fill="#9c2f62">  pathology:</text>
    <text x="50" y="256" fill="#9c2f62">    enabled: true</text>
    <text x="50" y="274" fill="#9c2f62">    datasets: [kather2016, …]</text>
    <text x="50" y="292" fill="#9c2f62">    target_microns_per_pixel: 0.5</text>
    <text x="50" y="314">audit:  review_budget: 0.10</text>
    <text x="50" y="332">        mri: {…}  pathology: {…}</text>
  </g>

  <!-- arrows to tracks -->
  <g stroke="#475569" stroke-width="2" marker-end="url(#a)">
    <line x1="332" y1="190" x2="418" y2="150"/>
    <line x1="332" y1="270" x2="418" y2="280"/>
  </g>

  <!-- track boxes -->
  <rect x="420" y="100" width="280" height="100" rx="12" fill="#eef4ff" stroke="#5b8def" stroke-width="2"/>
  <text x="440" y="125" font-weight="700" fill="#2f5bb7">--track mri</text>
  <text x="440" y="148" fill="#1e293b">MriTrackConfig</text>
  <text x="440" y="168" fill="#1e293b">geometry: VolumeGeometry</text>
  <text x="440" y="188" fill="#1e293b">spacing_mm · orientation · shape</text>

  <rect x="420" y="230" width="280" height="100" rx="12" fill="#fdf0f5" stroke="#c2417b" stroke-width="2"/>
  <text x="440" y="255" font-weight="700" fill="#9c2f62">--track pathology</text>
  <text x="440" y="278" fill="#1e293b">PathologyTrackConfig</text>
  <text x="440" y="298" fill="#1e293b">geometry: TileGeometry</text>
  <text x="440" y="318" fill="#1e293b">µm/px · level · tile_x/y · channels</text>

  <!-- arrows to contract -->
  <g stroke="#475569" stroke-width="2" marker-end="url(#a)">
    <line x1="702" y1="150" x2="788" y2="200"/>
    <line x1="702" y1="280" x2="788" y2="230"/>
  </g>

  <!-- shared contract -->
  <rect x="790" y="150" width="280" height="130" rx="12" fill="#eefbf1" stroke="#1a7f37" stroke-width="2"/>
  <text x="810" y="175" font-weight="700" fill="#166534">CaseRecord (shared)</text>
  <text x="810" y="198" fill="#1e293b">case_id · track · modality</text>
  <text x="810" y="218" fill="#1e293b">geometry: Volume | Tile</text>
  <text x="810" y="238" fill="#1e293b">synthetic · source</text>
  <text x="810" y="262" fill="#166534" font-size="12">validated: track ↔ modality ↔ geometry must agree</text>

  <text x="550" y="385" text-anchor="middle" font-size="12" fill="#64748b">Turn a track off in the config and every --track command for it refuses with a clear message; the other track is untouched.</text>
</svg>
"""

if __name__ == "__main__":
    write_svg("two_track_config", SVG)
