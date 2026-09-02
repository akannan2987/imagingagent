[← README](../../README.md) · [All docs in order](../../README.md#the-tutorial-in-order) · [Glossary](../00-glossary.md)

# Phase 0 — The skeleton: a project that runs before it does anything

**Prerequisites:** your operating system's setup guide
([Windows](../01-setup-windows.md) · [macOS](../01-setup-macos.md) ·
[RHEL 8](../01-setup-rhel8.md)) and [the Git workflow](../03-git-workflow.md).
**Learning goal:** after this phase you can explain what every file in the
repository is for, why the project is shaped as layers, and you can run,
test, lint and inspect it from the command line.
**Time:** about 1.5 hours reading and typing.

---

## Why a phase with no imaging in it?

Professionals build the frame before the walls. A project that can be
installed, tested and inspected on day one is one you can extend safely:
every later phase adds a module, a test and a tutorial, and the frame
catches mistakes immediately. This phase is that frame. It also fixes the
design rules the whole roadmap depends on, so they never need retrofitting:

1. **Configuration, not constants.** Anything that could change lives in one
   YAML file and is validated when loaded.
2. **One storage interface.** Nothing reads or writes the disk directly.
3. **Typed contracts.** Cases, findings and reports are validated data
   shapes that can describe themselves to any caller.
4. **A run ledger.** Every run leaves a line saying what ran, with which
   settings, on which machine.
5. **The command line is a thin skin** over package functions that other
   front doors (a web server, an MCP server) will reuse unchanged.

---

## 1. The layout, file by file

Open the project in your editor and compare with this map. Every file is
listed; nothing in the repository is unexplained.

```
imagingagent/
├── .github/workflows/ci.yml     tests on Windows, macOS, Linux at every push
├── .gitignore                   what Git must never track (data, venv, caches)
├── CHANGELOG.md                 what changed in each version
├── CONTRIBUTING.md              branch model, daily loop, release flow
├── LICENSE                      MIT — anyone may use this, with attribution
├── README.md                    the front page
├── pyproject.toml               how the package is built, its dependencies, tool settings
├── requirements.txt             exact library versions (runtime)
├── requirements-dev.txt         exact versions for testing and linting
├── configs/default.yaml         the run configuration, every value commented
├── data/                        raw / interim / processed — empty, kept by .gitkeep
├── runs/                        run outputs and the ledger — empty, kept by .gitkeep
├── models/                      trained weights (later) — empty
├── docs/                        this tutorial
├── src/imagingagent/            the package
│   ├── __init__.py              version number and a map of the layers
│   ├── config.py                typed configuration
│   ├── storage.py               the storage interface + local-disk backend
│   ├── schemas.py               the data contracts
│   ├── ledger.py                the run ledger
│   ├── cli.py                   the command line
│   ├── utils.py                 hashing, timestamps, identifiers
│   └── py.typed                 marker: this package ships type hints
└── tests/                       one test file per module
```

**Why `src/`?** With the package in `src/`, Python cannot import it by
accident from the repository root; it must be installed (`pip install -e .`).
That guarantees the tests exercise the *installed* package — the same
thing a stranger gets — not a folder that happens to be nearby.

**Why `.gitkeep`?** Git tracks files, not folders. An empty folder vanishes.
A zero-byte `.gitkeep` file keeps the folder in the repository so the layout
exists the moment someone clones.

---

## 2. `pyproject.toml` — the build recipe

Open it. Four things to notice:

- `[project]` names the package, its version (`0.1.0`), and
  `requires-python = ">=3.11,<3.13"` — installing on the wrong Python fails
  immediately with a clear message instead of failing mysteriously later.
- `dependencies` lists only what Phase 0 needs. Later phases add extras;
  the skeleton stays light.
- `[project.scripts]` creates the `imagingagent` command: it points at
  `imagingagent.cli:app`, meaning "the object called `app` inside
  `src/imagingagent/cli.py`".
- `[tool.pytest.ini_options]` and `[tool.ruff]` configure the test runner
  and the linter, so `pytest` and `ruff check .` need no arguments.

**Do this:** change nothing yet, but run:

```bash
python -m pip show imagingagent
```

**Success looks like:** `Name: imagingagent`, `Version: 0.1.0`, and
`Editable project location: ...your folder...`. That last line is editable
mode working: the command runs your source files directly.

---

## 3. `config.py` and `configs/default.yaml` — what a run does

A **configuration** is the set of values that steer a run: where data is,
which dataset, how many cases a reviewer can afford to look at. Two
principles:

- **Typed.** `config.py` declares each value's type and allowed range using
  pydantic (a library that turns "a dictionary of text" into checked Python
  objects). A YAML typo like `review_budget_fraction: 10` is rejected at
  load time with a readable error.
- **Hashed.** `ProjectConfig.content_hash()` fingerprints the configuration.
  The ledger records it, so "which settings produced this result?" always
  has an answer.

**Do this:**

```bash
imagingagent config show --config configs/default.yaml
```

**Success looks like:** the configuration printed as JSON with every default
filled in. Now break it on purpose — create a file `configs/bad.yaml` containing:

```yaml
audit:
  review_budget_fraction: 10
```

and run `imagingagent config show --config configs/bad.yaml`.

**Success looks like** an error mentioning `review_budget_fraction`,
`Input should be less than or equal to 1`, and exit code 2. Delete
`configs/bad.yaml` afterwards. That refusal is the feature.

**Precedence** (highest first): `--config path`, then the environment
variable `IMAGINGAGENT_CONFIG`, then built-in defaults. Try the second:

| Windows (PowerShell) | macOS / Linux (bash) |
|---|---|
| `$env:IMAGINGAGENT_CONFIG="configs/default.yaml"` | `export IMAGINGAGENT_CONFIG=configs/default.yaml` |
| `imagingagent doctor` | `imagingagent doctor` |
| `Remove-Item Env:IMAGINGAGENT_CONFIG` | `unset IMAGINGAGENT_CONFIG` |

The `config` line of the output should now name the file instead of
"built-in defaults".

---

## 4. `storage.py` — where bytes live

Every module writes through `Storage`, an **interface**: a promise of six
operations (`write_bytes`, `read_bytes`, `exists`, `delete`, `list_keys`,
`local_path`) without saying how they are done. `LocalStorage` fulfils the
promise with a folder on disk. A future object-storage backend will fulfil
it with a cloud bucket, and nothing else in the pipeline will change.

Keys look like `runs/abc/report.json` — forward slashes on every operating
system. `pathlib` converts to Windows backslashes internally.

`validate_key` rejects `..`, absolute paths and backslashes. **Why:** the
storage root is a boundary. A key like `../../etc/passwd` must never reach
the disk. Six of the tests exist only to prove this.

**Do this** — a hands-on experiment in the Python interpreter:

```bash
python
```

```python
from imagingagent.storage import LocalStorage
s = LocalStorage("scratch")
s.write_json("demo/hello.json", {"greeting": "hi"})
s.list_keys("demo")
s.read_json("demo/hello.json")
s.write_text("../escape.txt", "no")   # expect StorageError
exit()
```

**Success looks like:** `['demo/hello.json']`, then `{'greeting': 'hi'}`,
then a `StorageError` for the escape attempt. Delete the `scratch` folder
afterwards.

---

## 5. `schemas.py` — the contracts

A **schema** is the declared shape of a piece of data: which fields, which
types, which are optional. Four contracts exist now:

| Contract | What it is | Used from |
|---|---|---|
| `CaseRecord` | one scan: id, image key, optional reference label, spacing, shape, whether synthetic | Phase 1 |
| `Finding` | one measured fact and whether it passed | Phase 4 |
| `AuditReport` | all findings for a case, a trust score, a verdict (`accept` / `review` / `reject`), a plain-language summary | Phase 4–6 |
| `RunRecord` | one ledger line | now |

They are pydantic models, so they validate on creation, serialise to JSON,
and can publish a **JSON Schema** — a machine-readable description of
themselves. That is what an agent needs to call a tool correctly, and it is
why the shapes are fixed now rather than invented later.

**Do this:**

```bash
python -c "from imagingagent.schemas import AuditReport; import json; print(json.dumps(AuditReport.model_json_schema(), indent=2)[:600])"
```

**Success looks like:** the beginning of a JSON document with
`"properties"` including `run_id`, `case_id`, `findings`, `score`, `verdict`.

---

## 6. `ledger.py` — the run history

`runs/ledger.jsonl` is **append-only**: each run adds a line when it starts
and another when it finishes, and no line is ever edited. JSONL is "one
JSON object per line" — trivial to append, and never half-corrupt. Each
line carries the run id, timestamp (UTC), command, config hash, package
version and platform.

**Do this:**

```bash
imagingagent init
imagingagent init
imagingagent ledger list
```

**Success looks like:** two runs listed, both `init`, both `finished`,
same config hash. Open `runs/ledger.jsonl` in your editor: four lines
(start + finish per run). That file is your provenance record; it is
ignored by Git (outputs are not source) but it travels with any run folder
you archive.

---

## 7. `cli.py` — the front door

The command line uses **Typer**, which turns a Python function into a
command: the function's parameters become options, its docstring becomes
`--help` text. Look at `doctor()` — it calls `load_config`, `resolve_config_path`,
`platform_summary`; it computes nothing itself. That is the design rule:
future front doors reuse the same functions.

**Do this:**

```bash
imagingagent --help
imagingagent doctor --help
```

**Success looks like:** the command list, then `doctor`'s options with the
help text taken from the docstring.

---

## 8. Tests — the safety net

`tests/` holds 31 tests, one file per module. A **unit test** is a tiny
program that calls one function with known input and asserts the output.
Run them:

```bash
pytest
```

**Success looks like:** `31 passed`. Now see what a failure looks like — in
`tests/test_config.py`, change `0.10` to `0.11` in `test_defaults_are_valid`,
run `pytest` again, read the report (it shows the expected and actual
values), then change it back. Knowing what a failure *looks like* before
you cause one for real is worth two minutes.

Useful variants: `pytest -x` stops at the first failure; `pytest tests/test_storage.py`
runs one file; `pytest -k unsafe` runs tests whose name contains `unsafe`.

One test deserves attention: `test_repo_default_yaml_matches_builtin_defaults`
loads `configs/default.yaml` and asserts its hash equals the code defaults.
If anyone changes one without the other, the suite fails. Small, cheap
tests that protect agreements between files are the best kind.

---

## 9. Lint and format — the spell-checker

**ruff** finds likely bugs (unused imports, undefined names) and enforces a
consistent style, so diffs show meaning, not whitespace.

```bash
ruff check .
ruff format --check .
```

**Success looks like:** `All checks passed!` and `N files already formatted`.
If `format --check` complains, run `ruff format .` to fix it automatically.

---

## 10. Continuous integration — the same checks, on three machines

`.github/workflows/ci.yml` tells GitHub to run, on every push to `master`,
`beta` or `develop`: install from scratch on Windows, macOS and Ubuntu,
lint, format-check, test, and smoke-test the command line. You never run
this file yourself; GitHub does, and shows a green tick or a red cross next
to each commit under the **Actions** tab.

**Why:** "works on my machine" is not evidence. Three fresh machines passing
the same suite is.

RHEL 8 is not a hosted runner; the RHEL guide plus the later container
phase cover it — stated in the workflow itself.

---

## 11. Two ways to run everything

This project keeps two paths open in every phase:

- **By hand:** the Python interpreter, one function at a time, as in
  sections 4–5. Best for learning and debugging.
- **Automatically:** the `imagingagent` command (and later the MCP server),
  which strings the same functions together. Best for reproducible runs.

Both call identical code. If they ever disagree, that is a bug.

---

## Checkpoint

- [ ] `python -m pip show imagingagent` shows an editable install
- [ ] `imagingagent config show --config configs/bad.yaml` refuses an out-of-range value
- [ ] the storage experiment raised `StorageError` for `../escape.txt`
- [ ] `imagingagent ledger list` shows your `init` runs
- [ ] `pytest` → `31 passed`; `ruff check .` → `All checks passed!`
- [ ] the Actions tab on GitHub shows a green run on `develop`

## What could go wrong

| Symptom | Cause | Fix |
|---|---|---|
| `imagingagent: command not found` | `.venv` not active | activate it (see your setup guide, Step 6) |
| `ModuleNotFoundError: No module named 'imagingagent'` | package not installed in this `.venv` | `python -m pip install -e .` |
| `pytest` collects 0 tests | run from the wrong folder | `cd` to the repository root |
| CI red on Windows only | a path with hard-coded `/` outside storage keys | use `pathlib`; keys stay forward-slash |
| `git push` rejected | remote has commits you lack | `git pull`, resolve, retry — never force-push |

## What you learned

Editable installs and `src/` layout; typed configuration with precedence
and hashing; a storage interface and why boundaries need guards; data
contracts that publish schemas; an append-only ledger; a thin CLI;
unit tests, linting, and continuous integration on three operating systems.

Next: [`01-phase-1-ingestion.md`](01-phase-1-ingestion.md) — real MRI
volumes land, with a synthetic stand-in for offline runs.

---

## End of phase — git

```bash
git switch develop
git add -A
git commit -m "phase-0: skeleton, typed config, storage abstraction, run ledger, CLI, tests, CI, setup and workflow docs"
git push origin develop develop:beta develop:master
# add --tags only when a release tag was created in this phase
git switch master
git pull --ff-only origin master
git switch develop
```
