[← README](../README.md) · [Handbook](HANDBOOK.md) · [Glossary](00-glossary.md)

# Tool cookbook — ready-to-run commands with expected output

Copy, paste, compare. Every command is run from the repository root with
the virtual environment active (`(.venv)` in the prompt). Commands are the
same on Windows, macOS and RHEL 8 unless a PowerShell variant is shown.

## Available now (Phase 0)

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
imagingagent config show --config configs/default.yaml
```
Prints the validated configuration as JSON with every default filled in.

```bash
imagingagent ledger list
```
```
run_id        started_at            command     status    config
3f2a9c1d7e0b  2026-09-06T14:03:22Z  init        finished  9fb4eea0e4ff
```

Using an environment variable instead of `--config`:

| bash | PowerShell |
|---|---|
| `export IMAGINGAGENT_CONFIG=configs/default.yaml` | `$env:IMAGINGAGENT_CONFIG="configs/default.yaml"` |
| `unset IMAGINGAGENT_CONFIG` | `Remove-Item Env:IMAGINGAGENT_CONFIG` |

## Development checks

```bash
pytest                      # 31 passed
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
