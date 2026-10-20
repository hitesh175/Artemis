# ARTEMIS Stage 5b — direct microphone / push-to-talk

This is a standalone helper for the Stage 5 project. It does **not** overwrite `main.py`, `runtime.py`, or the ONNX wake-word model.

1. Extract ZIP to `C:\Users\kanag\Desktop\Artemis`.
2. ` .\.venv\Scripts\python.exe ptt_artemis.py --list-devices`
3. ` .\.venv\Scripts\python.exe ptt_artemis.py`
4. Press ENTER to begin; say **Open Notepad** once; press ENTER to stop. First run previews transcription and cannot execute any command.
5. Once accurate: ` .\.venv\Scripts\python.exe ptt_artemis.py --execute` and repeat.

Uses the existing offline cached faster-whisper `base.en` model. Audio remains in memory and is not saved. Default device is the system Windows default input device; specify `--device N` to choose the built-in microphone when necessary.
