# Artemis Stage 2 — "Hey Artemis" (offline, no trained custom model yet)

This is an **incremental patch** to the already-working ARTEMIS Stage 1 Windows project. It upgrades the *voice wake phrase* and preserves your Windows command allowlist, virtual environment, and speech models. **The wake detector now uses Vosk's speech-to-text results**, rather than a purpose-trained "Hey Artemis" ONNX wake model. Speech recognition may mishear the name or consume more CPU than a dedicated detector.

## Install in the EXISTING ARTEMIS folder

1. Stop Artemis with Ctrl+C. **Back up** the entire existing project folder if you edited its code.
2. Download this patch ZIP into your Downloads folder.
3. In VS Code, open your existing ARTEMIS project (the folder with `main.py`, `artemis`, and `.venv`). Open PowerShell and run:

   ```powershell
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage2_patch.zip" -DestinationPath . -Force
   ```

   You may instead use Windows Explorer to extract the ZIP and copy its contents into the project folder, replacing the matching source files. **Do not delete `.venv` or `models`.** If you downloaded the ZIP into another directory, adjust the command path accordingly.

4. Make sure your project still has `artemis/commands.py`, `artemis/microphone.py`, `artemis/speech.py`, `artemis/voice.py`, and `models/vosk-model-small-en-us-0.15`. The patch does not include them because they are already working.

5. Test the pure command parser and wake-phrase matching:

   ```powershell
   .\.venv\Scripts\python.exe -m unittest discover -s tests -v
   .\.venv\Scripts\python.exe main.py --text
   ```

6. **Safely diagnose wake recognition first, without launching apps**:

   ```powershell
   .\.venv\Scripts\python.exe main.py --wake-test
   ```

   Say **"Hey Artemis"**, then pause. Look for `[Wake test SUCCESS]`. Ctrl+C ends the test.

7. If the wake test succeeds, run the normal hands-free mode:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

   Say **"Hey Artemis"**, pause briefly, then say **"open Notepad"**. You should hear a response and Notepad should open.

## If Artemis is not detected

Use the *diagnostic transcript mode*:

```powershell
.\.venv\Scripts\python.exe main.py --wake-test --wake-debug
```

Say the phrase 4-5 times and see what Vosk transcribes. The English small model may not know the word `Artemis`. If it consistently transcribes a specific **two-or-more-word** substitute such as `hey art miss`, you can cautiously add that full variant to `WAKE_ALIASES` in `artemis/config.py`:

```python
WAKE_ALIASES = ("hey artemis", "hey art miss")
```

Add **only** phrases that your own diagnostics repeatedly show; aliases increase false activations. Avoid very broad substitutes like `hey artist` or `hey`. This is a temporary workaround until we train a dedicated keyword model. You can run the old Stage 1 "Hey Jarvis" model via `--wake-mode jarvis` if installed, e.g.:

```powershell
.\.venv\Scripts\python.exe main.py --wake-mode jarvis
```

If the fallback model is missing, you can download it once using:

```powershell
.\.venv\Scripts\python.exe setup_models.py --include-jarvis
```

## Other options

- `--list-devices`: list available audio input/output devices.
- `--device N`: choose a microphone by index shown in the device list.
- `--no-voice`: print rather than speak replies.
- `--wake-mode vosk`: default offline recognition for "Hey Artemis".
- `--wake-test`: do **not** execute any commands; diagnose recognition only.
- `--wake-debug`: show microphone-derived transcripts in terminal while testing; do not use if you don't want speech displayed.
- `Ctrl+C`: immediately stop the microphone listener.

## Privacy and safety

- Audio processed locally; no cloud AI calls in `main.py`.
- Microphone buffers remain in RAM, no audio files are recorded or uploaded by ARTEMIS.
- Stage 1 approved Windows commands remain unchanged; wake-test does not run actions.
- **Potential false wakes:** this is phrase recognition, not secure voice authentication. Avoid running it near conversations or loud media until tested.
- This uses the CPU **continuously** for Vosk STT, so battery impact may be higher than the old trained "Hey Jarvis" model. It does not require the RTX GPU. When we train a dedicated local wake model, we can restore more efficient standby behavior.
- It will not listen if the program is closed or Windows is asleep.

## Next phase

Build and evaluate a **locally trained custom "Hey Artemis" wake-word ONNX model** (or obtain a trustworthy locally hosted one), then integrate it into the existing `wakeword.py` interface; subsequently add microphone tray controls, chatbot GUI, and local Ollama AI.
