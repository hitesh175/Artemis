# Artemis Stage 5: One-sentence voice commands

This patch is designed to install **over Stage 4**. It keeps your `hey_artemis.onnx` and existing strict commands. Its new transcription path preserves ~2.8 seconds of audio preceding the wake hit, continues listening after activation, transcribes the full segment with the already installed local faster-whisper model, strips "Hey Artemis" from the beginning, and passes the remaining text to the allowlisted command executor.

## Install (Windows PowerShell, project root)

1. Stop Artemis using Ctrl+C. Download this ZIP to `Downloads`.
2. Back up your current `main.py` and `artemis/runtime.py` (the ZIP does not replace main.py).
3. `Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage5_one_sentence_patch.zip" -DestinationPath . -Force`
4. ` .\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_streaming_command.py" -v`
5. ` .\.venv\Scripts\python.exe main.py --stt whisper --wake-threshold 0.15`

Test: say "Hey Artemis, open Notepad" naturally, once. For the old style, say "Hey Artemis", pause briefly, then "Open Notepad". For safety, recognized commands are still restricted to the existing allowlist.

`[Heard]` shows the unedited Whisper transcript. `You:` shows what remains after stripping the initial wake phrase. No audio is saved to disk. If the wake model fails to activate, audio capture cannot recover it; we will then need to calibrate or retrain the wake model with your real voice, rather than endlessly lowering the threshold.

**Limitations:** Stage 5 still uses the existing synthetic-trained wake classifier, whose first-attempt accuracy is not guaranteed; endpointing uses an RMS threshold (not a neural VAD); no multi-turn conversational agent or TTS-engine change is included. The existing `Speaker` performs spoken replies if pyttsx3/SAPI5 is working, and the voice can be disabled with `--no-voice`. Always-on microphone input stays local. First-time Whisper model download still requires internet; subsequent inference uses `local_files_only=True`.
