# Figure generators

Every illustration under `docs/img/` is produced by a script in this folder,
never drawn by hand and pasted. Regenerate one with:

```bash
python scripts/figures/<name>.py        # writes docs/img/<name>.svg
python scripts/figures/all.py           # regenerates every figure
```

Why scripts? Three reasons: a figure can be edited by changing text and
rerunning; a figure carries no hidden metadata; and a figure that depends on
data (later phases) is regenerated from the run that produced the numbers.

| Script | Writes | Used in |
|---|---|---|
| `cover_imagingagent.py` | `docs/img/cover_imagingagent.svg` | README banner |
| `architecture.py` | `docs/img/architecture.svg` | README, `02-architecture.md` |
| `geometry_voxel_vs_pixel.py` | `docs/img/geometry_voxel_vs_pixel.svg` | `02-architecture.md` |
| `review_budget_funnel.py` | `docs/img/review_budget_funnel.svg` | `02-architecture.md`, Handbook |
| `git_branch_model.py` | `docs/img/git_branch_model.svg` | `03-git-workflow.md`, Handbook |
| `setup_flow.py` | `docs/img/setup_flow.svg` | the three setup guides |
| `datasets_map.py` | `docs/img/datasets_map.svg` | `08-data-and-models.md` |
| `two_track_config.py` | `docs/img/two_track_config.svg` | Phase 0c tutorial |

Each script writes with `newline="\n"` so the SVG is byte-identical on every
operating system.
