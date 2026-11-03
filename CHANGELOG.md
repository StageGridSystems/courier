# Changelog

All notable changes to Courier are documented in this file.

## [0.1.0] - 2026-11-03

### Added

- Windows Setup.exe via PyInstaller ONEDIR + Inno Setup, with Start Menu /
  optional desktop shortcuts, Apps and Features registration, and a GitHub
  Actions workflow that uploads `Courier-Setup-<version>.exe`.
- Live compose preview via QtWebEngine (`EmailPreview`), with QTextBrowser
  fallback that inlines remote images.
- Initial Courier desktop app by StageGrid Systems (PySide6).
- Authentication tab with Desktop OAuth client JSON (drag/drop or manual),
  `gmail.send` + userinfo email scopes, keyring / encrypted-file token storage.
- Clear rejection of service-account JSON with guidance toward Desktop clients.
- Audience tab with Gmail-style chips, paste extraction, CSV/XLSX/XLS/TXT import
  scanning every cell, named lists, suppression list, search, export.
- Compose/Send with HTML + plain text, merge fields, attachments, drafts/templates,
  test-to-admins, confirmation modal, background queue with pause/resume/cancel,
  retries on 429/5xx, resumable jobs, results CSV export.
- Settings for test audience, rate, daily cap, footer, theme, dry-run, data folder,
  full config export/import with optional password-encrypted auth.
- Built-in how-to guide covering Google Cloud setup, limits, deliverability, troubleshooting.
- Autosave via platformdirs, global exception handler with log file.
- `run.sh` / `run.bat`, PyInstaller spec and build scripts, pytest suite, ruff config.
