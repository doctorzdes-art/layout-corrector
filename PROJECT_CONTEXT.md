# PROJECT_CONTEXT — Layout Corrector (handoff for AI assistant)

> **For the AI:** read this file first in any new session. It summarizes the
> project history, architecture, conventions and open tasks.
> The user talks in **Ukrainian** — answer in Ukrainian.

## 1. What this is
**Layout Corrector** is a Windows tray app (Python 3 + PyQt6) that fixes text
typed in the wrong keyboard layout (e.g. `ghbdtn` → `привіт`), UA ↔ EN ↔ RU.

- Current version: **1.14** (`APP_VERSION` in `config.py`)
- Public repo: https://github.com/doctorzdes-art/layout-corrector (branch `main`, MIT)
- SHA-256 of `LayoutCorrector v1.14.exe`:
  `611BDD62B08CE0591CC82D7D8641F5A821707DFE1A4261964E04AF408794280F`
- Feedback form: `FEEDBACK_URL` in `config.py` (Google Forms)
- Update check: Google Drive folder `UPDATE_FOLDER_URL` (via `gdown`); version is
  parsed from exe file names like `LayoutCorrector v1.13.exe`.

## 2. Default hotkeys
| Action | Hotkey |
|---|---|
| Fix layout of selected text / last word | `Ctrl+Alt+Z` |
| Show converted text in popup (no replace) | `Ctrl+Alt+X` |
| Change case | `Ctrl+Alt+C` |

All hotkeys are configurable in the Settings window.

## 3. Architecture
| File | Role | Platform |
|---|---|---|
| `main.py` | `AppController`: tray icon/menu, signal wiring, update check, single-instance check | cross-platform (Qt) |
| `config.py` | `AppConfig` (settings JSON), logging, autorun (`winreg`), version helpers | **Windows-specific** (`winreg`) |
| `hotkey_listener.py` | Global hotkeys, `SendInput`, clipboard copy/paste, caret handling, layout switch | **Windows-specific** (`ctypes.windll.user32`) |
| `translator.py` | `LayoutTranslator`: character maps UA/EN/RU | cross-platform |
| `ui_settings.py` | `SettingsWindow`, `KeySequenceEdit` | cross-platform (Qt) |
| `ui_popup.py` | `TextPopup` | cross-platform (Qt) |
| `run.bat` | creates `venv`, installs deps, runs app with `pythonw` | Windows |
| `build.bat` | PyInstaller `--onefile --noconsole` → `LayoutCorrector v1.14.exe` | Windows |

Runtime paths:
- Settings: `%USERPROFILE%\.layout_corrector_settings.json`
- Log: `%LOCALAPPDATA%\LayoutCorrector\app.log` (rotating, 1 MB)

## 4. How to set up on a new machine
1. Install Python 3.10+ (tick "Add to PATH") and Git.
2. Unpack this archive (or `git clone` the repo).
3. Run `run.bat` → creates `venv`, installs `requirements.txt`, starts the app.
4. Build exe: `build.bat` (needs `venv` from step 3).
5. Git identity used in this repo (local config, re-set on new PC if needed):
   `git config user.name "LayoutCorrector Developer"`,
   `git config user.email "developer@layoutcorrector.local"`.
   Pushing to GitHub requires the user to log in (Git Credential Manager popup).

## 5. Release checklist (when bumping version, e.g. 1.14)
1. Update `APP_VERSION` in `config.py`.
2. Update name `LayoutCorrector vX.YY` in `build.bat` (2 places + copy line).
3. Run `build.bat`, test the exe.
4. `git commit`, `git tag -a vX.YY -m "..."`, `git push origin main --tags`.
5. Create GitHub Release, attach exe, paste SHA-256 (`Get-FileHash <exe> -Algorithm SHA256`)
   and a VirusTotal link.
6. Upload exe to the Google Drive update folder (so in-app update check sees it).

## 6. History / decisions so far
- v1.0 → v1.1 → v1.12 → v1.13 built and distributed via Google Drive.
- Aug 2026: published source on GitHub for trust; added `.gitignore`, `README.md`, `LICENSE` (MIT).
  `.gitignore` excludes `venv/`, `build/`, `dist/`, `*.exe`, `*.spec`, `*.log`.
- Trust advice given to user: VirusTotal scan link in release notes, SHA-256,
  repo "About" description + topics, screenshots in README.
- **macOS port**: a friend with a Mac will build it with Antigravity. Only source
  files are needed. `hotkey_listener.py` must be rewritten for macOS
  (Quartz Event Taps / `pynput`, Accessibility permission), `winreg` autorun in
  `config.py` → LaunchAgent plist; layout switching via TIS APIs; build `.app` with PyInstaller.

- Nov 2026: **v1.14** built on the new Windows PC:
  - Smart clipboard snapshot & restore via `QClipboard`/`QMimeData` (preserves screenshots/images, copied files, HTML, colors, custom formats) + Windows 10/11 Clipboard History (`Win+V`) & Cloud Clipboard exclusion flags (`ExcludeClipboardContentFromMonitorProcessing`, `CanIncludeInClipboardHistory`, `CanUploadToCloudClipboard`).
  - Fixed `is_processing` concurrency lock across listener and main Qt threads (with 5s safety timeout).
  - Upgraded `_simulate_ctrl_key` to use `SendInput` with hardware scancodes and explicit Left/Right modifier VK release/restore.
  - Capped `Shift+Left` re-selection (`MAX_RESELECT_STEPS = 2000`) and chunked allocation to prevent `SendInput` flooding.
  - Fixed multiline case toggle (`Ctrl+Alt+C`), scheduled weekly update checks, settings window checkbox sync from tray menu, HTML escaping in update dialog, and strict JSON settings validation.
- A separate macOS port already exists in sibling folder `layout_corrector_macos`
  (repo https://github.com/doctorzdes-art/layout-corrector-macos, 1 commit,
  based on **v1.12**, has `.github/workflows/build-mac.yml`, `build.sh`, `run.sh`).
  It lags behind Windows v1.13 — changes from 1.13 need to be ported.

## 7. Open ideas / TODO
- Screenshots in README; repo About/topics on GitHub (user to do via web UI).
- Optional: GitHub Actions workflow to build the exe automatically on tag push
  (would further increase trust — build is reproducible from public source).
- Optional: macOS version (see above).
