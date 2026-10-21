ARTEMIS Stage 7.1.4 — conversational voice cleanup

WHAT CHANGES
- Removes emojis, markdown and leaked thinking tags from spoken text only.
- Speaks in short sentence chunks instead of waiting for an entire long answer.
- Changes Alba speaking pace from length_scale 1.12 to 0.98.
- Reuses Piper model in the current Python process.
- Keeps the existing Windows output-device selector (ARTEMIS_OUTPUT_DEVICE).

INSTALL
1. Back up C:\Users\kanag\Desktop\Artemis\artemis\voice.py
2. Extract this ZIP into C:\Users\kanag\Desktop\Artemis\ (project root).
3. Confirm the file is at artemis\voice.py.
4. Test: .\.venv\Scripts\python.exe -m artemis.test_artemis_audio_713
5. Start: .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_711.py

NOTE
This reduces TTS-related latency but cannot eliminate Ollama response generation or
Whisper transcription time. Chunking may leave a tiny audible pause between
sentences. It does not change your microphone, LLM or app controls.
