ARTEMIS STAGE 7.1 — CONVERSATIONAL PLANET

Unzip these three Python files into:
  C:\Users\kanag\Desktop\Artemis\artemis\

Run from project root:
  .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_710.py

REQUIRES:
 - Ollama running locally at http://127.0.0.1:11434
 - A working custom model named artemis (`ollama list`)
 - Existing ARTEMIS files and dependencies from Stage 6.5.1

Test with 'Hello Artemis, how are you?' and then 'What did I just ask you?'
Try 'Open Spotify' to test the existing allowlisted Windows app resolver.
Uncheck Allow approved commands for preview mode. Check Speak responses for TTS.

Privacy: Conversation history stays in memory and is erased when app closes.
No cloud API calls: all prompts go to local Ollama server.
No arbitrary application launching through model output.

Limitations: Speaking is turn based; microphone pauses during transcription,
model generation and speech. No barge-in during TTS. Offline information may
be outdated; the model has no web tool. Recognition is still base.en Whisper.
If Ollama is not running, Artemis gives a helpful failure response.

Existing Stage 6.5.1 files are NOT overwritten: new launcher has a new name.
