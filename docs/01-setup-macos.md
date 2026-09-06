[← README](../README.md) · [Handbook](HANDBOOK.md) · [All docs in order](../README.md#the-tutorial-in-order) · [Glossary](00-glossary.md)

# 01 — Setup on macOS (Intel or Apple Silicon), from a blank machine

**Prerequisites:** a Mac where you can install software, an internet
connection, about 45 minutes. Nothing else — not Python, not Git.
**Learning goal:** a working "workshop": Python 3.11, Git, VS Code, a GitHub
account, the ImagingAgent code, an isolated Python environment, and a
passing test suite proving it all works.

Windows users: [`01-setup-windows.md`](01-setup-windows.md). RHEL 8:
[`01-setup-rhel8.md`](01-setup-rhel8.md).

---

## How to read this page

Every step: **what**, **how** (exact command), **why**, **what success looks
like**, **if it fails**. Do them in order and never skip a verification.

Commands run in **Terminal** (Finder → Go menu → Utilities → Terminal,
or press `Cmd+Space`, type `Terminal`, Enter). A line ending in `$` or `%`
is the prompt; you type only what follows it.

**Intel or Apple Silicon?** Apple menu → About This Mac. "Chip: Apple M1/M2/M3/M4"
is Apple Silicon; "Processor: Intel" is Intel. Both work; there is no GPU
acceleration for the deep-learning phases on either, and the project is
designed for that (small volumes, CPU training in minutes).

---

## Step 1 — Install the Xcode Command Line Tools (gives you Git)

**What:** Apple's command-line developer tools, which include Git.

**How:**

```bash
xcode-select --install
```

A dialog appears; click **Install** and wait (a few minutes).

**Verify:**

```bash
git --version
```

**Success looks like:** `git version 2.3x.x (Apple Git-xxx)`

**If it fails:** `xcode-select: error: command line tools are already
installed` → good, they are there; move on.

**Tell Git who you are** (stamped on every commit) and set the default
branch name to match this project:

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch master
```

---

## Step 2 — Install Python 3.11

**What:** the Python interpreter. macOS ships an old Python for its own use;
never rely on it — install your own.

**How:** download the **macOS 64-bit universal2 installer** for the latest
3.11.x from <https://www.python.org/downloads/macos/> and run it with
defaults. On the final screen, the installer opens a folder; double-click
**Install Certificates.command** (it lets Python download from HTTPS sites
— needed when Phase 1 fetches data).

**Why python.org and not Homebrew?** Homebrew upgrades Python underneath you
without asking, which breaks virtual environments. The python.org installer
stays at the version you chose.

**Verify** (open a new Terminal window):

```bash
python3.11 --version
```

**Success looks like:** `Python 3.11.9` (any 3.11.x)

**If it fails:** `command not found` → the installer did not finish, or the
Terminal window predates it. Open a new window; if still missing, rerun the
installer.

---

## Step 3 — Install Visual Studio Code

**What:** a free code editor with a built-in terminal and Git view.

**How:** download from <https://code.visualstudio.com/>, unzip, drag
**Visual Studio Code** into the Apps folder in Finder's sidebar. Open it, press `Cmd+Shift+P`, type
`shell command`, choose **"Shell Command: Install 'code' command in PATH"**.
Then `Cmd+Shift+X`, search **Python** (Microsoft), Install.

**Verify:** in a new Terminal, `code --version` prints a version.

---

## Step 4 — Create a GitHub account and a personal access token

1. <https://github.com/signup> → create the account, verify the email.
2. Avatar → **Settings** → **Developer settings** → **Personal access tokens**
   → **Tokens (classic)** → **Generate new token (classic)**. Note
   `imagingagent laptop`, expiration 90 days, scope **repo**. Generate and
   **copy it now** — shown once. Store it in a password manager. Never put it
   in a file inside the repository.
3. Let macOS remember it for Git:

```bash
git config --global credential.helper osxkeychain
```

The first `git push` asks for username (your GitHub username) and password
(paste the token); the Keychain remembers it afterwards.

---

## Step 5 — Choose a project folder and get the code

```bash
mkdir -p ~/projects
cd ~/projects
```

`~` is your home folder (`/Users/you`).

**Option A — clone from GitHub:**

```bash
git clone https://github.com/akannan2987/imagingagent.git
cd imagingagent
```

**Option B — you already have the project folder** (an unpacked archive):
move it into `~/projects` and:

```bash
cd ~/projects/imagingagent
```

**Verify:** `ls` shows `pyproject.toml configs src tests docs ...`

---

## Step 6 — Create the virtual environment

**What/why:** a `.venv` is a sealed toolbox — this project's Python and
libraries, isolated from every other project. Delete the folder and it is
gone cleanly.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

**Success looks like:** the prompt starts with `(.venv)`. Activate it in
every new Terminal window you use for this project.

---

## Step 7 — Install ImagingAgent and its tools

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

`-e .` installs the project in editable mode: the `imagingagent` command
runs the code in `src/` directly, so edits take effect without reinstalling.

**Verify:** `imagingagent version` → `imagingagent 0.1.0`

**If it fails:** `command not found: imagingagent` → `.venv` not active.
`source .venv/bin/activate` and retry.

---

## Step 8 — Health check and tests

```bash
imagingagent doctor --config configs/default.yaml
imagingagent init
pytest
```

**Success looks like** (abridged):

```
imagingagent 0.1.0
platform     : Darwin-23.x / CPython 3.11.9
python       : 3.11 ok
...
result       : healthy
created  data/raw
...
ledger   runs/ledger.jsonl (run 3f2a9c1d7e0b)
...............................                                          [100%]
31 passed in 0.2s
```

Optional libraries `not installed` are expected — each phase adds its own.

**If it fails:** `python : 3.9 TOO OLD` → the `.venv` used the wrong
Python. `deactivate`, `rm -rf .venv`, redo Step 6 with `python3.11`.

---

## Step 9 — Open in VS Code

```bash
code .
```

Bottom-right, click the Python version and pick `.venv/bin/python`.
`` Ctrl+` `` opens the built-in terminal with `.venv` active.

---

## Step 8b — Installing a track's extra libraries (later phases)

The core installs in seconds because imaging libraries are **optional
extras**, installed only when a phase needs them. When a phase tutorial
says "install the mri extras" (or pathology, or serve), run, with `.venv`
active:

```bash
python -m pip install -r requirements-mri.txt          # NIfTI/DICOM, MONAI, PyTorch (CPU)
python -m pip install -r requirements-pathology.txt    # slide readers, InstanSeg, embeddings, spatial
python -m pip install -r requirements-serve.txt        # MCP server, review interface
```

These files arrive with Phase 1, pinned and verified on all three
operating systems. `imagingagent doctor` then shows the libraries under
their track heading. On an Intel Mac PyTorch runs on CPU only; on Apple
Silicon it can use the built-in accelerator (`--device mps`) but every
tutorial's budget assumes CPU.

---

## The short daily loop

```bash
cd ~/projects/imagingagent
source .venv/bin/activate
git switch develop
git pull
# ... work ...
pytest
```

---

## Checkpoint

- [ ] `python3.11 --version` prints 3.11.x
- [ ] `git --version` works and `git config user.name` prints your name
- [ ] prompt shows `(.venv)` after activation
- [ ] `imagingagent doctor --config configs/default.yaml` ends with `result       : healthy`
- [ ] `pytest` ends with `31 passed`

Next: [`03-git-workflow.md`](03-git-workflow.md), then
[`04-phase-tutorials/00-phase-0-skeleton.md`](04-phase-tutorials/00-phase-0-skeleton.md).
