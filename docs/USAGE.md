# Using Artemis

[Project overview](../README.md) · [Windows setup](../setup/FIRST_RUN.md)

## Choose how to interact

| Control | What it does |
| --- | --- |
| Chat / Ctrl + K | Open text conversation. |
| Quiet mode | Block microphone recording and spoken replies; stop current speech. |
| Microphone | Start push-to-talk recording; click again to stop and transcribe. |
| Automatically send recognized speech | Submit a transcript automatically when allowed by the current interaction mode. Otherwise, review it in chat. |
| Hands-free | Start repeated listening/answering turns. Off by default; Quiet mode blocks it. |
| Stop reply | Stop the current streamed chat reply; it does not undo desktop actions. |
| Stop speaking | Interrupt speech and pause hands-free. |
| Mini Artemis | Switch to a compact window with optional pinning. |

Prepare cached voice models in Settings before a conversation if desired. Actual recording/playback requires suitable models and working devices. The setup guide explains the separate model downloads.

## Memory

Facts are saved only through explicit commands. Ordinary chat does not automatically create memories.

```text
remember that I prefer tea
show memories
find memories about tea
update memory 1: I prefer coffee
forget memory 1
```

Use the ID returned by your own app when updating or deleting. Relevant facts may inform subsequent model replies. Clearing a conversation does not remove saved facts; deleting a fact does not remove old chat messages that mention it.

## Documents

Use Settings → Documents → Choose files to index. Supported input includes UTF-8 text/Markdown up to 200 KB and PDF/Word `.docx` up to 5 MB per file. Scanned/image-only PDFs need OCR, which is not included.

```text
search documents for budget
list documents
remove document 1
```

The index is a local snapshot. Select a changed file again to refresh it. Excerpts include text lines, PDF pages, or Word paragraph/table locations. Removing an entry leaves the original file untouched. Model-generated answers and citations should be checked against the supplied excerpts.

## Reminders and briefings

```text
remind me in 10 minutes to stretch
show reminders
cancel reminder 1
daily briefing
```

Reminders persist locally. Due notices are visual and remain until dismissed; overdue reminders appear after reopening. Artemis must be open to display them.

A daily briefing combines weather for the saved city, due/overdue reminders, and events from imported calendars. A schedule can be enabled in Settings for a silent daily notice. It does not create an OS background task or automatically start speech.

## Calendar snapshots

Import an `.ics` export through Settings → Calendar. Reimport it when the source calendar changes.

```text
calendar today
list calendars
remove calendar 1
```

This feature reads imported snapshots, including supported recurring events. It does not connect to or edit a live calendar account.

## Everyday tools and apps

```text
weather today
weather tomorrow
what time is it
what is the date
calculate (25 + 15) / 2
open Notepad
```

Set the weather city in Settings. Weather needs internet and sends location searches/coordinates to Open-Meteo. App discovery is limited to the installed-app resolver's results; close matches require confirmation.

## Reviewed task plans

```text
plan tasks: what time is it; calculate 25 * 4; open Notepad
```

Review the two-to-four-step preview before clicking Run. Supported read operations include time/date, weather, arithmetic, briefings, calendar, reminders, memory, and document search. App opening is allowed only at the end. Plans do not accept arbitrary shell commands, memory edits, or reminder creation.

A failed step stops the plan. Cancel stops subsequent steps after the current operation returns and does not undo completed work. Restored chat text cannot replay a plan.

## When something needs attention

- **No chat reply:** use Settings → Service status; check that Ollama is running and the selected model is installed.
- **Missing voice model:** follow the setup guide, then use Voice preparation. Do not interpret a service-status check as a microphone/speaker test.
- **Slow responses:** use Performance to inspect session timings. Voice-model loading and local inference need CPU/RAM resources.
- **Outdated document/calendar information:** reimport the source file; both features use snapshots.

See [current validation limits](../README.md#validation--next-steps) before relying on unattended use.
