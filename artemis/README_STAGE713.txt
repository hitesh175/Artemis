ARTEMIS Stage 7.1.3 — Diagnosable Piper playback

Extract the artemis folder contents over your existing project's artemis folder.
Only replaces artemis/voice.py; adds artemis/test_artemis_audio_713.py.

From the Artemis project root, with the current .venv:
  .\.venv\Scripts\python.exe -m artemis.test_artemis_audio_713

The test plays a short tone and then synthesizes/speaks with Piper.
It also prints every output device and the generated waveform's duration and peak.

If needed, choose a listed output device using PowerShell:
  $env:ARTEMIS_OUTPUT_DEVICE = "DEVICE_NUMBER"
  .\.venv\Scripts\python.exe -m artemis.test_artemis_audio_713

Remove the override:
  Remove-Item Env:ARTEMIS_OUTPUT_DEVICE

After successful sound test:
  .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_711.py

The speaker remains offline. No generated audio files are saved.
