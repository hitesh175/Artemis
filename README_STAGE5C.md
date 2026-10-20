# ARTEMIS Stage 5c — offline British female Piper voice

This patch replaces only `artemis/voice.py`, retaining the `Speaker(enabled=True).say(message)` interface used by Stage 5 and Stage 5b. It adds `test_piper_voice.py`.

## Install (Windows PowerShell, at project root)

1. Back up existing `artemis/voice.py` first.
2. Extract this zip to project root using `Expand-Archive`.
3. ` .\.venv\Scripts\python.exe -m pip install piper-tts`
4. Download BOTH files to `models\voices` (as described in chat): `en_GB-alba-medium.onnx` and `en_GB-alba-medium.onnx.json`.
5. ` .\.venv\Scripts\python.exe test_piper_voice.py`
6. ` .\.venv\Scripts\python.exe ptt_artemis.py --execute`

If a local Piper model file is not present or cannot load, it uses the existing Windows pyttsx3 SAPI5 voice. Inference stays offline once the files are installed.

Your wake detection and Whisper pipeline are untouched.
