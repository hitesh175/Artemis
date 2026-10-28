# Artemis

Windows desktop assistant with local Ollama chat, Whisper recognition, Kokoro/Piper
speech, opt-in hands-free, Mini mode, Quiet mode, app launching and everyday tools.

## Source of truth

Make future application changes in **app/**. This is a source snapshot of the active
Desktop installation taken on 28 October 2026. SOURCE-BASELINE.json records the
original file hashes. The installed application remains at Desktop/Artemis and
has not been replaced or restarted by this consolidation.

The existing Artemis-* folders, ZIP updates and baseline/ are historical reference
packages. They remain in place and are excluded from the new Git repository.
Their README claims do not establish current application behavior. The inactive
music service and older wake-word/orb experiments are excluded from app/.

## Development and verification

Use Python 3.11 x64 on Windows. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/check.py
.\.venv\Scripts\python.exe scripts/build.py
```

requirements-baseline.lock captures the entire existing Python environment for
reference, including legacy packages. It is not a minimal dependency lock or a
verified clean-machine install. requirements.txt lists the active direct runtime
dependencies; fresh-environment installation remains to be validated.

## Running a development copy

Run `python app/run_logged.py` using an environment with the dependencies installed.
This starts a separate development instance; close the installed app first to
avoid microphone/device contention. Its settings and logs live under app/, and
existing private conversation history is not copied.

Ollama must be running with the `artemis` model. Microsoft Edge WebView2 is required.
For Kokoro, set ARTEMIS_KOKORO_DIR to a directory containing kokoro-v1.0.onnx and
voices-v1.0.bin. Piper fallback expects models/voices/en_GB-alba-medium.onnx and
its configuration under app/. Whisper may download its configured model on first
use; pre-cache it for offline operation. Model weights are not included.

## Packaging

scripts/build.py writes output/releases/artemis-source.zip with a SHA-256 manifest.
It uses stable file ordering and timestamps. This is a source distribution, not a
self-contained installer. It excludes private settings, conversations, logs,
Python environments and model weights. No install or deployment is performed.

## Next steps

1. Shared tool interface and bounded task execution.
2. Streamed replies, cancellation and service diagnostics.
3. Explicit personal memory and document search with citations.
4. Persistent reminders and daily briefings.

ARCHITECTURE.md describes the earlier installed baseline. Its historical workspace
section predates this consolidation; use app/ for current development.
