# ARTEMIS Stage 6 — Windows desktop GUI

Standalone desktop interface for **your existing Stage 5b/5c Artemis project**. Requires `artemis/commands.py`, `artemis/streaming_command.py`, `artemis/voice.py` and cached faster-whisper `base.en`. It does not replace `main.py`, runtime.py, or your trained wake-word model.

## Windows PowerShell install

```powershell
cd "$env:USERPROFILE\Desktop\Artemis"
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage6_desktop_gui.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m pip install PySide6
.\.venv\Scripts\python.exe artemis_desktop.py
```

The interface starts in **preview mode**: text and voice are processed through your existing safe command allowlist, but nothing launches until **Allow approved commands** is checked.

Click **Start recording**, say **Open Notepad** without a wake word, then click **Stop recording**. The recording stays in memory and is discarded after transcription. Processing runs in a Qt worker thread. A 15-second safety cap prevents runaway recording.

Use the text box to send approved commands, such as `help`, `open notepad`, and `what time is it`. This is **not yet an open-ended AI chatbot** and conversation history is only kept in the running app's memory; closing the app clears it. To get spoken replies, check **Speak responses**. If Piper isn't installed/tested, the voice module can fall back to Windows TTS.

If Whisper's cached model is unavailable, run Stage 4's `main.py --prepare-whisper` once. The GUI uses cached `base.en` offline and intentionally doesn't download models itself. Microphone defaults to the Windows default input (the Realtek microphone array on your tested setup).

## Troubleshooting

- `ModuleNotFoundError: PySide6`: install it in the *same* `.venv`.
- Microphone missing/quiet: Windows Settings > System > Sound > Input; and Privacy & security > Microphone.
- `Could not find model ... local_files_only`: prepare Whisper once in the same Windows user account.
- If the window freezes or throws an error, paste the VS Code terminal traceback.

The existing hands-free/wake-word mode remains available through `main.py` independently.
