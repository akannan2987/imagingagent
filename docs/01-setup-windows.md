[← README](../README.md) · [All docs in order](../README.md#the-tutorial-in-order) · [Glossary](00-glossary.md)

# 01 — Setup on Windows (10 or 11), from a blank machine

**Prerequisites:** a Windows computer where you can install software, an
internet connection, about 45 minutes. Nothing else — not Python, not Git.
**Learning goal:** by the end you have a working "workshop": Python 3.11,
Git, VS Code, a GitHub account, the ImagingAgent code, an isolated Python
environment, and proof (a passing test suite) that everything works.

If you are on macOS use [`01-setup-macos.md`](01-setup-macos.md); on
RHEL 8 Linux use [`01-setup-rhel8.md`](01-setup-rhel8.md).

---

## How to read this page

Every step has the same shape: **what** to do, **how** (the exact command),
**why** it matters, **what success looks like**, and **if it fails**.
Do the steps in order. Do not skip a verification — the whole point of a
setup guide is that you *know* each layer works before adding the next.

Commands are shown for **PowerShell**, the Windows command line. Open it by
pressing the Windows key, typing `PowerShell`, and pressing Enter. A window
with a blinking cursor appears: type a command, press Enter, read the result.
A line starting with `PS C:\Users\you>` is the *prompt* — you do not type
that part, only what comes after it.

---

## Step 1 — Install Python 3.11

**What:** Python is the programming language ImagingAgent is written in. You
need the interpreter — the program that runs Python code.

**How:**

1. Open <https://www.python.org/downloads/windows/> in a browser.
2. Under "Python 3.11" (the latest 3.11.x), download **"Windows installer (64-bit)"**.
3. Run the installer. On the first screen **tick "Add python.exe to PATH"**
   (bottom of the window) — this is the step people miss — then click
   **Install Now**.
4. Close the installer when it says "Setup was successful".

**Why 3.11 and not the newest?** Every library the later phases use supports
3.11 on all three operating systems, and 3.11 is the version RHEL 8 ships.
One version everywhere means one set of instructions and no surprises.

**Verify** — open a *new* PowerShell window (PATH changes only apply to new
windows) and run:

```powershell
py -3.11 --version
```

**Success looks like:**

```
Python 3.11.9
```

(any 3.11.x is fine)

**If it fails:**
- `'py' is not recognized` → the installer did not add Python to PATH. Rerun
  the installer, choose **Modify**, and tick "Add Python to environment
  variables"; then open a new PowerShell window.
- It prints a different version, e.g. `Python 3.12.x` → you have several
  Pythons. That is fine; `py -3.11` always picks 3.11 explicitly, and we use
  it in every command below.

---

## Step 2 — Install Git

**What:** Git records the history of your code — every meaningful change is
a snapshot you can return to. Think of it as a save-game system.

**How:**

1. Open <https://git-scm.com/download/win> and download the 64-bit installer.
2. Run it. Accept the defaults on every screen **except** one: on
   "Adjusting the name of the initial branch in new repositories", choose
   **"Override the default branch name"** and type `master`. (Keep this
   consistent with the project's branch model.)
3. The default editor question can stay as-is (Vim) — we will use VS Code
   through Git's own settings later.

**Verify** — in a new PowerShell window:

```powershell
git --version
```

**Success looks like:** `git version 2.4x.x.windows.1`

**Tell Git who you are** (this name and email are stamped on every commit):

```powershell
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch master
git config --global core.autocrlf true
```

**Why `core.autocrlf true`?** Windows ends text lines differently from
macOS/Linux. This setting converts on the way in and out so a file edited on
Windows does not show every line as changed when viewed on Linux.

---

## Step 3 — Install Visual Studio Code

**What:** VS Code is a free code editor: a text editor that understands
Python, shows Git changes, and has a built-in terminal.

**How:** download from <https://code.visualstudio.com/> and run the installer
with defaults. Tick **"Add to PATH"** if offered.

Then open VS Code, press `Ctrl+Shift+X` (Extensions), search for
**Python** (publisher: Microsoft) and click Install.

**Verify:** in PowerShell, `code --version` prints a version number.

---

## Step 4 — Create a GitHub account

**What:** GitHub hosts Git repositories online. It is where your code lives
publicly and where continuous integration (automatic testing on every push)
runs for free.

**How:**

1. Go to <https://github.com/signup> and create an account. Choose a username
   you are happy to have on your work.
2. Verify the email address GitHub sends you.
3. Create a **personal access token** — the password Git uses when pushing:
   - Click your avatar (top right) → **Settings** → **Developer settings**
     → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
   - Note: `imagingagent laptop`. Expiration: 90 days. Scope: tick **repo**.
   - Click Generate and **copy the token now** — it is shown only once. Keep
     it somewhere safe (a password manager). It is a secret: never paste it
     into a file inside the repository.

Git for Windows includes **Git Credential Manager**, which will ask for this
token the first time you push and then remember it.

---

## Step 5 — Choose a project folder and get the code

**What:** a folder for all your projects, and the ImagingAgent code inside it.

**How:**

```powershell
mkdir $HOME\projects
cd $HOME\projects
```

`$HOME` is your user folder (`C:\Users\you`). Now get the code — one of two ways:

**Option A — clone from GitHub** (the normal way once the repository is online):

```powershell
git clone https://github.com/akannan2987/imagingagent.git
cd imagingagent
```

**Option B — you already have the project folder** (for example an archive
you unpacked): move that `imagingagent` folder into `$HOME\projects` and:

```powershell
cd $HOME\projects\imagingagent
```

**Verify:**

```powershell
dir
```

**Success looks like:** you see `pyproject.toml`, `configs`, `src`, `tests`,
`docs` in the listing.

**If it fails:** `cd : Cannot find path` → the folder is somewhere else;
find it in File Explorer, right-click the folder → "Copy as path", and
`cd` to that path in quotes.

---

## Step 6 — Create the virtual environment

**What:** a virtual environment (`.venv`) is a private copy of Python plus
the exact libraries this project needs, kept inside the project folder.

**Why:** every project needs different libraries in different versions. Put
them all in one shared Python and they fight. A `.venv` is a sealed toolbox
per project: nothing you install here affects any other project, and
deleting the folder removes everything cleanly.

**How:**

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Success looks like:** the prompt now begins with `(.venv)`. That prefix
means "commands run inside the toolbox". You activate it every time you open
a new terminal to work on the project.

**If it fails** with `... cannot be loaded because running scripts is
disabled on this system`: PowerShell blocks scripts by default. Run this
once, then retry the activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Answer `Y`. This allows locally created scripts (like the activation script)
while still blocking unsigned scripts downloaded from the internet.

---

## Step 7 — Install ImagingAgent and its tools

**What:** install the pinned libraries, then install the project itself in
"editable" mode, so the `imagingagent` command always runs the code in
`src/` — edit a file, the command changes; no reinstall needed.

**How** (prompt must show `(.venv)`):

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
```

The `-e` means editable; the `.` means "this folder".

**Verify:**

```powershell
imagingagent version
```

**Success looks like:** `imagingagent 0.1.0`

**If it fails:**
- `imagingagent : The term ... is not recognized` → the `.venv` is not
  active (no `(.venv)` in the prompt). Run `.\.venv\Scripts\Activate.ps1`.
- `pip` reports a network error → check the connection; corporate networks
  sometimes need a proxy: `$env:HTTPS_PROXY="http://proxy.example.com:8080"`
  then retry.

---

## Step 8 — Run the health check and the tests

**What:** `doctor` checks Python, the config and the folders; `pytest` runs
every automated test in `tests/`.

**How:**

```powershell
imagingagent doctor --config configs/default.yaml
imagingagent init
pytest
```

**Success looks like** (abridged):

```
imagingagent 0.1.0
platform     : Windows-11 / CPython 3.11.9
python       : 3.11 ok
config       : configs/default.yaml
...
result       : healthy
created  data/raw
...
ledger   runs/ledger.jsonl (run 3f2a9c1d7e0b)
...............................                                          [100%]
31 passed in 0.2s
```

The optional libraries listed as `not installed` are expected: each later
phase installs its own.

**If it fails:**
- `python       : 3.9 TOO OLD` → the `.venv` was made with the wrong Python.
  Deactivate (`deactivate`), delete it (`Remove-Item -Recurse -Force .venv`)
  and redo Step 6 with `py -3.11`.
- One test fails with a path containing `\` → you are running an old copy
  of the code. Pull the latest (`git pull`) and rerun.

---

## Step 9 — Open the project in VS Code

```powershell
code .
```

VS Code opens the folder. Bottom-right, click the Python version and select
the interpreter at `.venv\Scripts\python.exe` so VS Code uses the same
toolbox as your terminal. Press `` Ctrl+` `` to open VS Code's built-in
terminal; it activates `.venv` automatically once the interpreter is set.

---

## The short daily loop (after setup, every session)

Setup is once. From now on, each working session is:

```powershell
cd $HOME\projects\imagingagent
.\.venv\Scripts\Activate.ps1
git switch develop
git pull
# ... work ...
pytest
```

---

## Checkpoint

You can tick all of these:

- [ ] `py -3.11 --version` prints 3.11.x
- [ ] `git --version` prints a version, and `git config user.name` prints your name
- [ ] the prompt shows `(.venv)` after activation
- [ ] `imagingagent doctor --config configs/default.yaml` ends with `result       : healthy`
- [ ] `pytest` ends with `31 passed`

Next: [`03-git-workflow.md`](03-git-workflow.md) — putting the code under
version control with the `master` / `beta` / `develop` model, then
[`04-phase-tutorials/00-phase-0-skeleton.md`](04-phase-tutorials/00-phase-0-skeleton.md).
