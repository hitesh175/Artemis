# ARTEMIS Stage 6.1 — GUI microphone diagnostics

This is a small patch for an installed Stage 6 Artemis desktop interface.

## Files
- `artemis_desktop.py` — updated desktop interface, uses shared microphone capture; shows audio duration, peak and RMS; adds Play last recording
- `artemis_audio_capture.py` — reusable in-memory audio recording/transcription helper

## Install in VS Code PowerShell

```powershell
cd "$env:USERPROFILE\Desktop\Artemis"
Copy-Item .\artemis_desktop.py .\artemis_desktop.py.stage6.backup -Force
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage6_1_mic_fix.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe artemis_desktop.py
```

Existing Stage 5 dependencies include numpy, sounddevice, faster-whisper, PySide6.

## Test
1. Disable **Allow approved commands** (preview mode).
2. Click Start recording, wait ~0.5 seconds, say "Open Notepad", click Stop.
3. Check new **Last recording** information at bottom (seconds, peak, RMS).
4. Click **Play last recording** to hear precisely what was recorded.
5. Compare transcription shown in chat. If it is correct, enable approved commands and retry.

Captured audio stays in RAM, and the last recording disappears when the app closes or when a new recording begins. It is not saved to disk.

## Notes
- Voice recognition has not yet been verified on the user's Windows hardware.
- This patch uses the same Whisper options and microphone stream settings as the working Stage 5b terminal PTT test. It does not guarantee improved transcription if the captured audio differs.
- The wake word remains separately handled by `main.py` and is not affected.
