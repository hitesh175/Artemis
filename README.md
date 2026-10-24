# Artemis desktop project

Start Artemis using its desktop or Start menu shortcut. `Artemis.pyw` is the console-free entry point; `start_artemis_v2.bat` is the diagnostic fallback.

## Current folders
- `desktop/`: active WebView2 desktop host, Python services and web interface.
- `artemis/`: shared application discovery, speech engines and legacy modules retained for compatibility.
- `.venv/`: installed Python environment. Keep this folder.
- `models/` and `voice_test/`: local AI/voice assets. `voice_test` is also searched by the active speech engine; keep it.
- `data/`: saved preferences, chat history, Mini position and utility settings.
- `logs/`: runtime diagnostics and single-instance lock. Keep these for troubleshooting.
- `tests/`: project checks.
- `ui-backups/`: rollback snapshots from updates.
- `_archive/`: historical distributions, old notes and staged backup files moved during cleanup.

`ARTEMIS-PROJECT-ARCHITECTURE.md` describes the main features and models. `ModelFile` configures the Ollama model. Requirements files, model setup helpers and older launch scripts are retained for maintenance and compatibility.

No model, saved chat, active code, installed environment or update backup was deleted during cleanup. The dated archive contains a manifest and Restore.ps1. To restore the old README files, first rename or move this new README.md; the restore script deliberately refuses to overwrite existing files. Close Artemis before restoring historical files.
