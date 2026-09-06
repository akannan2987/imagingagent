[← README](../README.md) · [Handbook](HANDBOOK.md)

# Uninstall — removing ImagingAgent cleanly

Nothing this project installs touches the system: everything lives in the
project folder, the virtual environment inside it, and a few library
caches. Remove in this order.

## 1. The project folder (includes the virtual environment, data, runs, models)

| macOS / RHEL 8 (bash) | Windows (PowerShell) |
|---|---|
| `rm -rf ~/projects/imagingagent` | `Remove-Item -Recurse -Force $HOME\projects\imagingagent` |

Anything you want to keep (a trained model, a run folder) — copy it out
first. The repository itself is on GitHub; cloning it again restores the
code but not data, runs or models (those are never committed).

## 2. Downloaded model weights kept in library caches (later phases)

| Cache | Location (bash) | Location (PowerShell) |
|---|---|---|
| Hugging Face (Phikon, PLIP, DINOv2) | `rm -rf ~/.cache/huggingface` | `Remove-Item -Recurse -Force $HOME\.cache\huggingface` |
| torch hub / torchvision (ResNet-50) | `rm -rf ~/.cache/torch` | `Remove-Item -Recurse -Force $HOME\.cache\torch` |
| InstanSeg models | `rm -rf ~/.instanseg` (if present) | `Remove-Item -Recurse -Force $HOME\.instanseg` |
| pip download cache (optional) | `python -m pip cache purge` | same |

Only delete a shared cache if no other project on the machine uses it.

## 3. Tools installed for the project (only if you no longer want them)

- **Python 3.11** — macOS: drag *Python 3.11* out of the Apps folder and remove `/Library/Frameworks/Python.framework/Versions/3.11`; Windows: *Settings → Apps → Python 3.11 → Uninstall*; RHEL 8: `sudo dnf remove python3.11 python3.11-pip python3.11-devel`.
- **Git** — macOS: part of the Xcode command-line tools, leave it; Windows: *Settings → Apps → Git → Uninstall*; RHEL 8: `sudo dnf remove git`.
- **VS Code** — macOS: drag to the bin; Windows: *Settings → Apps*; RHEL 8: `sudo dnf remove code` and delete `/etc/yum.repos.d/vscode.repo`.

## 4. Git identity and credentials (optional)

`git config --global --unset user.name`, `--unset user.email`; the stored
GitHub token: macOS Keychain Access → search "github"; Windows Credential
Manager → Windows Credentials → github; RHEL 8: delete `~/.git-credentials`
if you used the `store` helper.

That is everything. No services, no registry entries, no system packages
beyond the three tools in step 3.
