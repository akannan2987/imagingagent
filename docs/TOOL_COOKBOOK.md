[← README](../README.md) · [Handbook](HANDBOOK.md) · [Glossary](00-glossary.md)

# Tool cookbook — ready-to-run commands with expected output

Copy, paste, compare. Every command is run from the repository root with
the virtual environment active (`(.venv)` in the prompt). Commands are the
same on Windows, macOS and RHEL 8 unless a PowerShell variant is shown.

## Available now (Phases 0–0c)

```bash
imagingagent --help
```
```
 Usage: imagingagent [OPTIONS] COMMAND [ARGS]...
 A quantitative imaging pipeline built to be operated by an agent.
 ╭─ Commands ─────────────────────────────────────────╮
 │ version   Print the package version.               │
 │ doctor    Check Python, the configuration, ...     │
 │ init      Create every folder the configuration... │
 │ config    Inspect the configuration.               │
 │ ledger    Inspect the run ledger.                  │
 ╰────────────────────────────────────────────────────╯
```

```bash
imagingagent version
```
```
imagingagent 0.1.0
```

```bash
imagingagent doctor --config configs/default.yaml
```
```
imagingagent 0.1.0
platform     : Darwin-23.6.0 / CPython 3.11.9       ← yours will differ
python       : 3.11 ok
config       : configs/default.yaml
config hash  : 9fb4eea0e4ff
folder       : data/raw           present
folder       : data/interim       present
folder       : data/processed     present
folder       : runs               present
folder       : models             present
optional     : nibabel    not installed  (Phase 1 — NIfTI reading)
...
result       : healthy
```
Exit code 0 = healthy. "not installed" for optional libraries is expected
until the phase that needs them.

```bash
imagingagent init
```
```
exists   data/raw
...
ledger   runs/ledger.jsonl (run 3f2a9c1d7e0b)
```
Safe to rerun; each run adds a ledger line.

```bash
imagingagent tracks --config configs/default.yaml
```
```
mri         : enabled
  dataset   : msd_task04_hippocampus (MRI, CC-BY-SA 4.0)
  spacing   : (1.0, 1.0, 1.0) mm
  synthetic : fallback on (20 cases, seed 20260901)
pathology   : enabled
  dataset   : kather2016             role=tissue   on   CC-BY 4.0
  dataset   : pannuke                role=nuclei   on   CC-BY-NC-SA 4.0
  dataset   : deepliif               role=ihc      on   recorded at download
  dataset   : mcmicro_exemplar001    role=mif      on   recorded at download
  dataset   : visium_hne             role=spatial  on   recorded at download
  resolution: 0.5 µm/px
  synthetic : fallback on (40 tiles, seed 20260904)
audit       : review budget 10%
```

```bash
imagingagent modalities                      # or: --track pathology
```
```
modality                track      geometry status       description
MRI                     mri        volume   implemented  Magnetic resonance imaging — soft tissue in 3D
SYNTHETIC               shared     volume   implemented  Generated stand-in data; ...
CT                      mri        volume   planned      Computed tomography — ...
...
HE                      pathology  tile     implemented  Haematoxylin and eosin — the standard tissue stain
...
```

```bash
imagingagent doctor --config configs/default.yaml --track mri
```
Same as `doctor`, but only the `[mri]` group of optional libraries is listed.
An unknown track name exits with code 2.

```bash
imagingagent config show --config configs/default.yaml
```
Prints the validated configuration as JSON with every default filled in.

```bash
imagingagent ledger list
```
```
run_id        started_at            command     track      status    config
3f2a9c1d7e0b  2026-09-06T14:03:22Z  init        shared     finished  1c0b7d2e9a4f
```
Add `--track mri` or `--track pathology` to see one track's runs only.

Using an environment variable instead of `--config`:

| bash | PowerShell |
|---|---|
| `export IMAGINGAGENT_CONFIG=configs/default.yaml` | `$env:IMAGINGAGENT_CONFIG="configs/default.yaml"` |
| `unset IMAGINGAGENT_CONFIG` | `Remove-Item Env:IMAGINGAGENT_CONFIG` |

## Development checks

```bash
pytest                      # 53 passed
python scripts/figures/all.py   # regenerate every illustration in docs/img/
pytest -x                   # stop at the first failure
pytest -k storage           # only tests with "storage" in the name
ruff check .                # All checks passed!
ruff format --check .       # N files already formatted
ruff format .               # fix formatting in place
```

## Arriving with their phases — command shapes fixed now

These do not exist yet; each phase tutorial documents them with real
output when it lands. The shapes are fixed so documentation written today
stays correct.

| Command | Phase |
|---|---|
| `imagingagent ingest --track mri [--synthetic]` · `--track pathology --dataset kather2016` | 1 |
| `imagingagent preprocess --track <track>` | 2 |
| `imagingagent segment --track mri --method classical\|unet\|import --import-path <file>` · `--track pathology --method classical\|instanseg\|import` | 3 |
| `imagingagent uncertainty --track mri` · `imagingagent repeatability --track mri` | 4 |
| `imagingagent features --track <track>` | 5 |
| `imagingagent embed --track pathology --model phikon\|dinov2\|resnet50\|plip` | 6 |
| `imagingagent spatial --track pathology` | 7 |
| `imagingagent multimodal --track <track>` | 8 |
| `imagingagent audit --track <track> --review-budget 0.10` | 9 |
| `imagingagent benchmark --track <track>` | 10 |
| `imagingagent report --run <run_id>` · `imagingagent serve mcp` · `imagingagent serve review` | 11 |

## Python, one function at a time

The command line is a thin skin; every command can be reproduced in the
Python interpreter — the by-hand path. Phase 0 example:

```python
from imagingagent.config import load_config
from imagingagent.storage import get_storage
from imagingagent.ledger import RunLedger

cfg = load_config("configs/default.yaml")
storage = get_storage(cfg.storage)
ledger = RunLedger(storage)
for record in ledger.latest_per_run().values():
    print(record.run_id, record.command, record.status)
```
