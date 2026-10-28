# Artemis

Windows desktop assistant with local Ollama chat, Whisper recognition, Kokoro/Piper
speech, opt-in hands-free, Mini mode, Quiet mode, app launching and everyday tools.

## Reference policy

OpenJarvis is an ideas-only reference. Do not copy its source, assets, documentation,
or implementation into Artemis. Develop changes from Artemis's existing code and
independently written implementations. API integration may follow the provider's
official protocol documentation. No OpenJarvis dependency has been introduced.

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

Use Python 3.11 x64 on Windows. Node.js is also required for JavaScript checks
(not for running Artemis). From the repository root:

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

The shared deterministic tool interface is implemented in app/desktop/tool_router.py.
The desktop bridge exposes handle_command and list_tools, retaining handle_app_command
for compatibility. Tools run in order: everyday (weather, date/time, arithmetic, help),
then apps. Unknown requests continue to chat; tool failures stop dispatch. Responses
include handled, reply, spoken_reply, tool and sources, preserving existing choices
and confirmation tokens. Existing tools default spoken_reply to their display text
and sources to an empty list; structured source metadata can be supplied by future
tools. A handled response does not imply the requested action succeeded.

This change is in the development source only. No model-selected tool execution,
multi-step task runner, or installation update has been introduced.

1. Bounded task execution after tool permissions and cancellation are designed.
2. Improve speech interruption and measure voice latency.
3. Explicit personal memory and document search with citations.
4. Persistent reminders and daily briefings.

## Streamed replies and service checks

Chat now streams display text through the local proxy. Speech starts only after a
complete reply. Stop reply cancels the client request, discards the incomplete turn
from saved context, and pauses hands-free mode. It does not undo desktop tool
actions or interrupt audio already playing. The proxy closes its upstream request
when it detects client disconnection; a stalled upstream read may take up to its
100-second timeout, so immediate cancellation of Ollama computation is not guaranteed.

Settings → Service status → Check services checks Ollama reachability and the
installed artemis model, and reports current recognition/speech state. It does not
open the microphone, play audio or claim that audio devices are verified. Checks
are on demand, with a three-second Ollama timeout. Legacy non-streaming clients
remain supported.

Protocol reference: https://docs.ollama.com/api/chat and https://docs.ollama.com/api/tags.
Automated checks use a fake model server and synthetic audio. Native desktop visual
checks and a live model/voice session have not been performed for this change.

ARCHITECTURE.md describes the earlier installed baseline. Its historical workspace
section predates this consolidation; use app/ for current development.
