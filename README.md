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
was preserved during initial consolidation; the later feature update is now installed as recorded below.

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
for compatibility. Tools run in order: daily briefing, reminders, document search, personal memory, everyday (weather, date/time,
arithmetic, help), then apps. Unknown requests continue to chat; tool failures stop dispatch. Responses
include handled, reply, spoken_reply, tool and sources, preserving existing choices
and confirmation tokens. Existing tools default spoken_reply to their display text
and sources to an empty list; structured source metadata can be supplied by future
tools. A handled response does not imply the requested action succeeded.

The completed features are now installed locally. No model-selected tool execution,
or multi-step task runner has been introduced.

1. Bounded task execution after tool permissions and cancellation are designed.
2. Use session timings to target voice delays and improve turn detection.
3. Validate native desktop behavior and real-model citation quality.
4. Calendar integration after validating the optional local briefing schedule.

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
Automated checks use a fake model server and synthetic audio. Installed WebView2 integration and a real local-model streamed reply have passed. Microphone capture and speech playback were not exercised.

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

Tests use temporary databases and a fake model. Installed desktop integration has passed; real-model memory citation accuracy still needs observation.

## Document search

Settings → Documents → Choose files to index opens the native file picker. Only
selected files are indexed; there is no folder scan or file watcher. Supported
formats are UTF-8 .txt/.md (200 KB), PDF and .docx (5 MB). The limit is 50 documents,
5,000 text chunks and one million extracted characters per file, with at most
100 PDF pages. PDF support requires pypdf from requirements.txt. The installed app now has pypdf 6.10.0, matching the extraction test version.

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
Installed WebView2 layout transitions and service integration passed. Native picker interaction and real-model citation accuracy still need manual verification.

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

## Local installation update

On 28 October 2026 the completed development features were copied into the existing
Desktop/Artemis installation. The update verified all 62 application file hashes
and installed pypdf 6.10.0 in its existing Python environment. Chats, preferences,
model files, executable and shortcuts were preserved.

Original files are backed up under:
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-171308`.
To roll back, close Artemis and run scripts/rollback-local.ps1 with that directory
as its -Backup argument. The rollback restores old files, removes unchanged newly
installed files, and keeps user data and the compatible PDF dependency.

scripts/install-local.ps1 is the repeatable update command; scripts/verify-installed.py
checks the installed source with temporary test data, a hidden WebView2 window,
audio disabled, and a short live local-model reply when Ollama is available.

## Persistent reminders

- `remind me in 10 minutes to stretch` creates a one-shot reminder. Minutes, hours
  and days are supported; a day means 24 elapsed hours, not a calendar recurrence.
- `remind me at 2026-10-29T09:00+01:00 to call Alex` uses an exact timestamp.
  A UTC offset is required so an ambiguous clock time cannot be silently guessed.
- `show reminders` lists active reminders, ten per page; `show reminders 2` continues.
- `cancel reminder 1` cancels an active reminder. Dismiss in the visual inbox
  acknowledges a due reminder. Cancelled/dismissed IDs are never reused.

Creation replies show the due time in the computer's local timezone with its UTC
offset. Reminders support future times within 366 days and 200 active reminders.
They persist in app/data/reminders.sqlite3, excluded from Git and release packages.
Ordinary conversation and model output cannot schedule reminders.

The desktop checks for due reminders every five seconds and on regaining visibility.
Up to ten due reminders appear in a persistent visual inbox; dismissing one lets
the next appear. An item more than a minute late is labeled overdue, including after
reopening. The inbox never starts speech or microphone capture, preserving Quiet
mode. A reminder is not consumed by polling; it remains until dismissed or cancelled.
The last 200 terminal records are retained; active reminders are never pruned.

This version requires Artemis to remain running. It does not wake the computer,
run while the app is closed, or send Windows notifications. Closed-app reminders
are shown after reopening; minimized/background views may delay when you see them.
One-shot reminders retain their exact instant if the computer timezone changes.
There are no recurring reminders, automatic task execution or external messages.

Tests cover timing boundaries, restart catch-up, persistence, acknowledgement,
cancellation, concurrency, malformed dates, explicit offsets, visual inbox behavior
and safe text rendering. The installed hidden desktop check verified the overdue inbox. User-visible timing and minimized-window behavior still need observation.

## Daily briefings

Say or type `daily briefing` or `morning briefing`, or open Settings → Daily briefing
→ Get daily briefing. The result contains the local date, weather for the saved
city, overdue reminders and reminders due later today. Up to five reminders in
each group are shown; `show reminders` provides the rest. It does not dismiss or
change reminders. Upcoming-today reminders use the computer's local date.

The briefing is assembled from real tool results, without an LLM. Weather uses
the existing Open-Meteo service and five-minute cache, with its data timestamp and
source shown in chat. Spoken output omits weather source/timestamp details and
follows the normal speech setting and Quiet mode. Missing city configuration prompts
you to set it. Weather or reminder failures are reported independently, preserving
the other available section. Reminder failure is never presented as an empty list.

On-demand briefings run when requested. Optional scheduling is described below.
Briefings do not connect email or calendars or invent news. Local date/reminder summaries work
without Ollama; weather still needs internet. Tests cover date boundaries, partial
failure, source attribution and reminder preservation, plus the installed button.

This feature is installed in Desktop/Artemis. Its rollback backup is
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-172203`.

## Ollama model selection

Settings → Local intelligence → Refresh models lists models reported by the local
Ollama service. Choose one and click Use selected model. Loading the settings does
not change the selection. `artemis` remains the default, including its `:latest`
alias. No model is downloaded or removed by this interface.

Selection is saved in app/data/model-settings.sqlite3 and applies to subsequent
chat requests, including streamed replies. An already running request keeps its
original model. Weather, reminders, memory commands, document search and daily
briefings continue to use deterministic tools independently of chat model choice.
Service diagnostics report the selected model and whether it is present.

The app talks only to its fixed localhost Ollama endpoint. It does not silently
switch models when one is missing, accept arbitrary inference server URLs, or
overwrite the selection after a failed/offline change. Model capabilities and
inference behavior depend on the selected Ollama model; live integration has been
verified with artemis. Existing chats and model files are preserved.

Installed update backup:
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-172938`.
Automated checks cover persistence, next-request model routing, invalid and missing
models, offline preservation, corrupt settings, and selector behavior. Installed
WebView2 checks use isolated settings so the user's selection is not changed.

## Stop speaking

During speech generation or playback, a floating Stop speaking button appears in
Full, Mini and compact views. It cancels the active speech turn and pauses
hands-free mode. It leaves the displayed reply and saved chat intact and does not
disable spoken replies for future turns. Quiet mode and muting speech now cancel
an active turn as well, rather than allowing its audio to finish.

Cancellation is checked before and after synthesis and between 1,024-frame output
blocks. Playback uses an owned OutputStream, so stopping Artemis does not call the
global sounddevice stop function. An in-progress model load or synthesis call may
finish its computation; its cancelled audio is discarded before playback. During
that interval the UI shows Stopping speech and blocks another speech worker. No
wake word, voice interruption command or acoustic echo cancellation is introduced.
Stop reply still cancels text generation; Stop speaking controls speech separately.

Automated tests cover mono/stereo playback abort, cancellation during synthesis,
worker isolation, retry and mute interruption. The installed native button was
verified with simulated speech. A silent zero-sample test also opened the real
installed audio output and cancelled it in 0.24 seconds; no microphone or audible
speech was used. This does not validate recognition or full speech quality.

Installed rollback backup:
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-173550`.
Output API reference: https://python-sounddevice.readthedocs.io/en/0.5.3/api/streams.html.

## Real-use quality check

scripts/check-real-use.py runs installed-model checks with isolated invented facts
and documents, then enumerates devices and performs in-memory Kokoro-to-Whisper
transcription. It never opens microphone capture or audible playback and does not
execute the synthesized commands. On 28 October 2026, recall/edit/deletion checks,
document answer/citation, a missing fact, an embedded-instruction case, and two
silent speech round trips passed. Results and latency samples are in
output/real-use-checks.json and output/real-use-summary.md.

This is limited sample evidence rather than a general accuracy/security guarantee.
Manual microphone input, accent/noise conditions and audible conversation quality
still require user-initiated testing in the running app. The quality check does not
modify or restart the installed application.

## Performance panel

Settings → Performance → Refresh timings shows chat, recognition and speech timings
from the current app session. Clear timings removes retained measurements; active
operations may add new records when they finish. No recording or speech is started
by refreshing or clearing this panel.

The panel retains at most 50 completed/error/cancelled/waiting operation records
in memory, without prompts, replies, transcripts, audio, file paths or model names.
It resets on restart. Each stage shows its latest operation and the average total
time of completed operations in the retained sample. Failed/cancelled/waiting
operations do not contribute to completed averages. Nothing is sent externally.

- Chat total is the server request duration, including retrieval and Ollama. First
  text is measured when the server receives its first content fragment, rather than
  when the screen paints it. Non-streamed replies do not report first-text timing.
- Recognition total includes recording and preparation, cached-model lookup/load,
  and transcription. Transcription includes consuming Whisper's lazy segments.
- Speech total includes model loading, synthesis and playback. Successfully
  completed synthesis/playback supplies separate timings; cancelled operations may
  have only total and model-loading measurements. Device buffering and waiting for
  shared model/playback locks may contribute to totals.

These are diagnostic samples, not benchmarks or guarantees of end-to-end voice
latency. Text commands handled by deterministic tools do not create chat-inference
measurements. A client disconnect is marked cancelled when the server detects it.

The panel is installed. Backup:
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-174506`.
Automated checks cover bounded/concurrent collection, content exclusion, outcome
averages and instrumentation. Installed WebView2 verification refreshes the panel
after a real streamed reply, with microphone and audible speech disabled.

## Optional scheduled briefings

Settings → Scheduled daily briefing has an enable checkbox and a local 24-hour
time. Choose both and click Save briefing schedule. It is off by default, and the
installation does not enable it. Time is interpreted in the computer's local
timezone rather than as a fixed UTC offset.

While Artemis is running, the page checks every 30 seconds and on regaining
visibility. Once due, it prepares the existing weather/reminder briefing and shows
a silent expandable Daily briefing ready notice. It never starts microphone input
or speech, including when Quiet mode is off. The notice contains the snapshot date
and remains until dismissed or replaced by a newer day's briefing. Disabling the
schedule removes the pending notice; re-enabling does not repeat a date already
prepared. Changing the time after preparation applies to the following day.

Schedule settings and the latest pending snapshot persist in
app/data/briefing-schedule.sqlite3, excluded from Git and releases. Reopening after
the chosen time prepares the current day's briefing. Missed days are not replayed
as a backlog. A previous pending snapshot may remain visible before today's due
time and is labeled with its date. A partial weather/reminder result is saved as
that day's snapshot; use daily briefing manually to refresh it. Generation failures
without a usable result are retried on the next check.

The app must be open: this does not install a Windows scheduled task, wake the
computer, run in the background after exit, or send system notifications. Background
WebView throttling can delay checks. A DST-skipped time runs on the next check;
repeated hours do not duplicate the date. Clock/date rollback does not reissue a
previously prepared date. Clearing conversation does not delete the schedule.

Tests cover disabled defaults, due-time boundaries, concurrent checks, persistence,
dismissal, catch-up, clock rollback and retry. Installed WebView2 verification uses
temporary settings to enable, display and dismiss a briefing without sound. The
user's real schedule remains off.

Installed rollback backup:
`C:\Users\kanag\Desktop\Artemis\ui-backups\before-integrated-features-20261028-174938`.


