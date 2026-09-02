[← README](../README.md) · [All docs in order](../README.md#the-tutorial-in-order) · [Glossary](00-glossary.md)

# 01 — Setup on Red Hat Enterprise Linux 8 (or Rocky/Alma 8), from a blank VM

**Prerequisites:** a RHEL 8 machine or virtual machine where you can run
`sudo` (administrator) commands, an internet connection, about 40 minutes.
**Learning goal:** a working "workshop": Python 3.11, Git, the ImagingAgent
code, an isolated Python environment, and a passing test suite. VS Code is
optional on a server VM; instructions are included for a desktop VM.

Windows: [`01-setup-windows.md`](01-setup-windows.md). macOS:
[`01-setup-macos.md`](01-setup-macos.md).

---

## How to read this page

Every step: **what**, **how**, **why**, **success**, **if it fails**. In
order; no skipped verifications. Commands run in a terminal (bash). `$` is
the prompt. `sudo` runs one command as administrator and will ask for your
password.

**Why RHEL 8 gets its own page:** RHEL 8's system Python is 3.6, which is far
too old, and must not be touched (the operating system itself uses it).
RHEL 8 offers newer Pythons side by side through "AppStream" modules; we
install 3.11 that way and leave the system Python alone.

---

## Step 1 — Update the package index and install Git

```bash
sudo dnf makecache
sudo dnf install -y git
git --version
```

**Success looks like:** `git version 2.4x.x`

```bash
git config --global user.name  "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch master
```

**If it fails:** `This system is not registered with an entitlement server`
→ RHEL needs a (free developer) subscription for `dnf`: `sudo subscription-manager register`
with your Red Hat account, then `sudo subscription-manager attach --auto`.
Rocky/Alma do not need this.

---

## Step 2 — Install Python 3.11

**What:** Python 3.11 from AppStream, alongside the untouched system Python.

```bash
sudo dnf install -y python3.11 python3.11-pip python3.11-devel
python3.11 --version
```

**Success looks like:** `Python 3.11.x`

**Why `python3.11-devel`?** Some libraries in later phases compile small
pieces of C during installation; `-devel` provides the headers they need.

**If it fails:** `No match for argument: python3.11` → the AppStream
repository is not enabled. Run `sudo dnf repolist` and make sure a line
containing `appstream` appears; on RHEL, enable it with
`sudo subscription-manager repos --enable rhel-8-for-x86_64-appstream-rpms`.

**Do not** run `alternatives --set python ...` or otherwise change what
`python3` points to; `dnf` and other system tools depend on it.

---

## Step 3 — (Desktop VMs only) Install Visual Studio Code

On a headless server, skip this; `nano` or `vim` is enough to edit files.

```bash
sudo rpm --import https://packages.microsoft.com/keys/microsoft.asc
sudo tee /etc/yum.repos.d/vscode.repo > /dev/null << 'REPO'
[code]
name=Visual Studio Code
baseurl=https://packages.microsoft.com/yumrepos/vscode
enabled=1
gpgcheck=1
gpgkey=https://packages.microsoft.com/keys/microsoft.asc
REPO
sudo dnf install -y code
code --version
```

Then in VS Code: `Ctrl+Shift+X` → search **Python** (Microsoft) → Install.

---

## Step 4 — GitHub account and personal access token

1. <https://github.com/signup> → create the account, verify the email.
2. Avatar → **Settings** → **Developer settings** → **Personal access tokens**
   → **Tokens (classic)** → **Generate new token (classic)**. Note
   `imagingagent vm`, expiration 90 days, scope **repo**. Generate and
   **copy it now** — shown once. Never store it in a file inside the repository.
3. Let Git remember it for this machine:

```bash
git config --global credential.helper 'cache --timeout=86400'
```

The first push asks for username (GitHub username) and password (paste the
token) and remembers it for 24 hours. For permanent storage on a machine
only you use: `git config --global credential.helper store` (the token is
then saved in plain text in `~/.git-credentials` — acceptable on a private
VM, not on a shared one).

---

## Step 5 — Project folder and the code

```bash
mkdir -p ~/projects
cd ~/projects
```

**Option A — clone:**

```bash
git clone https://github.com/akannan2987/imagingagent.git
cd imagingagent
```

**Option B — you already have the folder** (unpacked archive, or copied
from another machine with `scp`):

```bash
cd ~/projects/imagingagent
```

**Verify:** `ls` shows `pyproject.toml configs src tests docs ...`

---

## Step 6 — Virtual environment

**What/why:** a `.venv` is a sealed toolbox — this project's Python and
libraries, isolated from the system and from other projects.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

**Success looks like:** prompt begins with `(.venv)`.

---

## Step 7 — Install ImagingAgent and its tools

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip install -e .
imagingagent version
```

**Success looks like:** `imagingagent 0.1.0`

**If it fails:**
- `command not found: imagingagent` → `.venv` not active.
- `pip` cannot reach PyPI → behind a proxy: `export HTTPS_PROXY=http://proxy.example.com:8080`
  then retry. Some corporate VMs also need `pip config set global.cert /path/to/ca-bundle.crt`.

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
platform     : Linux-4.18.0-xxx / CPython 3.11.x
python       : 3.11 ok
...
result       : healthy
created  data/raw
...
ledger   runs/ledger.jsonl (run 3f2a9c1d7e0b)
...............................                                          [100%]
31 passed in 0.2s
```

**If it fails:** `python : 3.6 TOO OLD` → the `.venv` used the system
Python. `deactivate`, `rm -rf .venv`, redo Step 6 with `python3.11`.

---

## Platform notes specific to RHEL 8

- **SELinux** is on by default and does not interfere with anything in this
  project (all files live in your home folder).
- **Firewalls:** nothing needs opening. Phase 6's servers bind to
  `localhost` only.
- **No GPU:** expected. The deep-learning phases run on CPU by design.
- **Continuous integration** runs on Ubuntu, not RHEL 8; this page plus the
  later container phase are how RHEL 8 is covered.

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

- [ ] `python3.11 --version` prints 3.11.x and `python3 --version` still prints 3.6.x (untouched)
- [ ] `git --version` works and `git config user.name` prints your name
- [ ] prompt shows `(.venv)` after activation
- [ ] `imagingagent doctor --config configs/default.yaml` ends with `result       : healthy`
- [ ] `pytest` ends with `31 passed`

Next: [`03-git-workflow.md`](03-git-workflow.md), then
[`04-phase-tutorials/00-phase-0-skeleton.md`](04-phase-tutorials/00-phase-0-skeleton.md).
