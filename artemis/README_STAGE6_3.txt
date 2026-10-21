ARTEMIS Stage 6.3 — GPU sphere preview

Keep Stage 6.2E safe. This package contains NEW filenames; do not overwrite working voice files.

1. Extract artemis_orb_gpu.py and artemis_orb_voice_gpu.py into C:\Users\kanag\Desktop\Artemis\artemis\
2. From the Artemis project root:
   .\.venv\Scripts\python.exe -m pip install PyOpenGL
   .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_gpu.py

Requires OpenGL 3.3 compatible graphics driver, PySide6, and your existing voice dependencies.
On Windows laptops you may need to assign python.exe to high-performance GPU in Windows Graphics settings.
The working Stage 6.2E remains available using artemis_orb_voice.py.

This is an experimental GPU renderer. Shader compilation and Windows GPU behavior have not been verified here.
The state colors and voice command logic come from Stage 6.2E. Audio listening level reacts in real time; speaking is state-animated, not true TTS waveform synced yet.
