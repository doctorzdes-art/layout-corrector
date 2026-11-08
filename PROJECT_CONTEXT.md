# PROJECT_CONTEXT — Layout Corrector (handoff for AI assistant)

> **For the AI:** read this file first in any new session. It summarizes the
> project history, architecture, conventions and open tasks.
> The user talks in **Ukrainian** — answer in Ukrainian.

## 1. What this is
**Layout Corrector** is a Windows tray app (Python 3 + PyQt6) that fixes text
typed in the wrong keyboard layout (e.g. `ghbdtn` → `привіт`), UA ↔ EN ↔ RU.

- Current version: **1.14** (`APP_VERSION` in `config.py`) / **UI Redesign v2 (Material 3 Expressive)**
- Public repo: https://github.com/doctorzdes-art/layout-corrector (branch `main`, MIT)
- SHA-256 of `LayoutCorrector v1.14.exe`:
  `9EAD447963446C0E6995DC31825E09DBC309EB9B0A6E4CC41FD6C483D9479A12`
- Feedback form: `FEEDBACK_URL` in `config.py` (Google Forms)
- Update check: Google Drive folder `UPDATE_FOLDER_URL` (via `gdown`); version is
  parsed from exe file names like `LayoutCorrector v1.13.exe`.

## 2. Default hotkeys
| Action | Hotkey |
|---|---|
| Fix layout of selected text / last word | `Ctrl+Shift+Z` |
| Show converted text in popup (no replace) | `Ctrl+Shift+X` |
| Change case | `Ctrl+Shift+C` |

All hotkeys are configurable in the Settings window.

## 3. Architecture & Files
| File | Role | Platform |
|---|---|---|
| `main.py` | `AppController`: tray icon/menu, signal wiring, update check, single-instance check, exit widget | cross-platform (Qt) |
| `config.py` | `AppConfig` (settings JSON), logging, autorun (`winreg`), version helpers | **Windows-specific** (`winreg`) |
| `hotkey_listener.py` | Global hotkeys, `SendInput`, clipboard copy/paste, caret handling, layout switch | **Windows-specific** (`ctypes.windll.user32`) |
| `translator.py` | `LayoutTranslator`: character maps UA/EN/RU | cross-platform |
| `ui_common.py` | Typography (Fixel font loading), SVG color tinting, shape compositing, QSS theme loader | cross-platform (Qt) |
| `ui_settings.py` | `SettingsWindow`: NavRail, Hotkeys & Options, Symmetric Layout Editor, Feedback Page | cross-platform (Qt) |
| `ui_popup.py` | `TextPopup`: 380px dark card, direction chip, strikethrough original, timer bar with hover-pause | cross-platform (Qt) |
| `ui_dialog.py` | `UpdateDialog`: custom 400px frameless dialog with 64px logo | cross-platform (Qt) |
| `theme.qss` | Complete QSS stylesheet matching Material 3 Expressive ("Neon Graphite" palette) | cross-platform (Qt) |
| `design_tokens.json` | Design tokens: colors, typography, border radiuses, spacing | cross-platform |
| `fonts/` | MacPaw Fixel Display (Bold, SemiBold, Medium) & Fixel Text (Regular, Medium, SemiBold) | TTF (OFL 1.1) |
| `icons/` | 20 SVGs for navigation, hotkeys, switches, check, copy, exit, external | SVG |
| `shapes/` | 3 Material Expressive shape backgrounds (`cookie9.svg`, `clover4.svg`, `flower6.svg`) | SVG |
| `run.bat` | creates `venv`, installs deps, runs app with `pythonw` | Windows |
| `build.bat` | PyInstaller `--onefile --noconsole` bundling assets → `LayoutCorrector v1.14.exe` | Windows |

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
  - Smart clipboard snapshot & restore via Win32 Clipboard API (preserves screenshots/images, copied files, HTML, colors, custom formats) + Windows 10/11 Clipboard History (`Win+V`) & Cloud Clipboard exclusion flags.
  - Fixed `is_processing` concurrency lock across listener and main Qt threads (with 5s safety timeout).
  - Safe keybd_event modifier release and restore during Ctrl+Shift+Z execution.
  - Capped `Shift+Left` re-selection (`MAX_RESELECT_STEPS = 2000`) and chunked allocation to prevent `SendInput` flooding.
  - Fixed multiline case toggle (`Ctrl+Shift+C`), scheduled weekly update checks, settings window checkbox sync from tray menu, HTML escaping in update dialog, and strict JSON settings validation.

- Nov 2026: **UI Redesign v2 (Material 3 Expressive / Neon Graphite)**:
  - Complete modern redesign implemented based on Claude Design handoff kit (`LayoutCorrector_Redesign`).
  - Integrated MacPaw Fixel typography (Display 700/600/500 and Text 600/500/400).
  - Replaced legacy `QTabWidget` with a vertical `NavRail` (96px) with 56×32 indicator pills and uncompromised logo.
  - Page 1: General options cards with animated SVG switches and popup duration stepper; Hotkey tiles with Material Expressive background shapes (`cookie9`, `clover4`, `flower6`), always-visible key chips, and in-place recording mode (`grabKeyboard`, Esc cancel).
  - Page 2: Symmetric unit-based layout editor with segmented toggle ("Звичайні | ⇧ Shift"), `CharKey` dual-character display without "?", and physical keyboard mapping.
  - Page 3: Feedback hero card with `cookie9` shape, Google Forms CTA, Snackbar toast notification, and 3 step cards with copyable version chip.
  - `TextPopup`: 380px width, `#18181D` card, 24px radius, direction chip, strikethrough original text, 22px translated text, full-width copy button, and 4px progress timer with hover-pause.
  - `UpdateDialog`: custom frameless translucent dialog with 64px logo and modern buttons.
  - Tray Menu: dark translucent styling, switch indicators, and red `#FFB4AB` exit action.
  - Fixed Ukrainian spelling: "Зворотний зв’язок" everywhere.
  - PyInstaller `--add-data` updated in `build.bat` to bundle fonts, icons, shapes, theme, and tokens.
