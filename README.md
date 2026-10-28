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
for compatibility. Tools run in order: document search, personal memory, everyday (weather, date/time,
arithmetic, help), then apps. Unknown requests continue to chat; tool failures stop dispatch. Responses
include handled, reply, spoken_reply, tool and sources, preserving existing choices
and confirmation tokens. Existing tools default spoken_reply to their display text
and sources to an empty list; structured source metadata can be supplied by future
tools. A handled response does not imply the requested action succeeded.

This change is in the development source only. No model-selected tool execution,
multi-step task runner, or installation update has been introduced.

1. Bounded task execution after tool permissions and cancellation are designed.
2. Improve speech interruption and measure voice latency.
3. Validate native desktop behavior and real-model citation quality.
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

## Personal memory

Memory is independent of saved conversations. Facts are saved only by explicit
desktop commands; model responses and ordinary conversation cannot write facts.

- `remember that I prefer tea` saves a fact and returns its ID.
- `show memories` lists the first ten; `show memories 2` shows the next page.
- `find memories about tea` finds up to ten keyword matches.
- `update memory 1: I prefer coffee` edits a fact by ID.
- `forget memory 1` removes it from future memory retrieval.

Facts persist in app/data/personal-memory.sqlite3, excluded from Git and releases.
The store supports 200 facts of up to 500 characters; duplicate facts reuse an ID.
Clearing chat does not clear memory. Forgetting memory does not remove earlier chat
messages, which may still be in recent context. Use Clear conversation as well when
you want to remove that context. Memory is ordinary local SQLite storage, not encrypted.

Local chat receives up to five keyword-matched facts (not semantic search). Facts
are labeled user reference data, separated from the system instructions and latest
question. The model is instructed to refer to used facts with `[Memory ID]`; actual
model adherence has not yet been verified. Memory commands work directly without
Ollama, including while Quiet mode is enabled. Saving a weather preference here
does not change the weather tool's configured city; use Settings → Everyday for that.

Tests use temporary databases and a fake model. Live desktop/model validation and
installation are pending.

## Document search

Settings → Documents → Choose files to index opens the native file picker. Only
selected files are indexed; there is no folder scan or file watcher. Supported
formats are UTF-8 .txt/.md (200 KB), PDF and .docx (5 MB). The limit is 50 documents,
5,000 text chunks and one million extracted characters per file, with at most
100 PDF pages. PDF support requires pypdf from requirements.txt. The original
installed application environment has not been changed; tests used bundled pypdf 6.10.

- `search documents for budget` returns up to three matching excerpts with file
  paths, document IDs, and source locations. This works without Ollama.
- `list documents` lists indexed IDs and paths; `list documents 2` shows page two.
- `remove document 1` deletes that snapshot from the index, keeping the source file.
- Choose the same file again to refresh its snapshot while preserving its ID.

The ordinary local chat request also retrieves up to three matching excerpts using
SQLite FTS5 keyword search. Excerpts are supplied as reference data, with instructions
to cite `[Document ID, line N]`, PDF `page N`, or Word `paragraph N` / `table N, row N`.
Word paragraph numbering counts top-level body paragraphs, including empty ones;
table rows count within each top-level body table. It does not invent page numbers.
An expandable reference section shows the actual
excerpts supplied to the model, including paths and indexing times; it does not
claim the model used every excerpt or verified its answer. Model citation accuracy
still requires live validation. Stored document text cannot invoke desktop tools.

app/data/documents.sqlite3 contains ordinary unencrypted local snapshots, excluded
from Git and release packages. No files are sent to a cloud service; selected
excerpts are passed to local Ollama. Removing an index does not erase excerpts or
answers already retained in chat; clear the conversation to remove that context.
Search uses indexed snapshots even if the original changes or disappears. Re-index
or remove the document explicitly when appropriate.

Automated tests cover indexing, text/PDF/Word citations, refresh, persistence, removals,
format/size limits, query escaping, a simulated picker and model context transport.
Old text-only indexes gain a companion location table without rebuilding their FTS data.
Failed extraction keeps the previous indexed snapshot.
The native picker UI, desktop layout, and real-model citation behavior have not
been tested live. Changes remain in development source; the installed app is unchanged.

PDF extraction reads existing text layers only. Encrypted PDFs, image-only scans
and legacy .doc files are unsupported. Blank PDF pages produce no excerpts; in a
mixed text/image document only extractable text is indexed. Text order, columns,
equations and tables may not match visual layout. Verify important details in the
original file. Word extraction covers main-body paragraphs and top-level table
rows; headers, footers, comments, footnotes, text boxes, nested tables and embedded
objects are outside this version's coverage. No macros, external relationships,
or document actions are executed.

PDF API reference: https://pypdf.readthedocs.io/en/stable/user/extract-text.html.
The tests validate extraction and locations rather than rendered document layout.
