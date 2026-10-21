ARTEMIS Stage 6.3.4 — Deep Matte Planet (safe renderer)

Installation:
1. Extract both .py files to C:\Users\kanag\Desktop\Artemis\artemis\
2. From the Artemis project root, run:
   .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_634.py

This version is separate from 6.3.3 and retains the same offline microphone,
Whisper, allowlisted command and optional voice playback implementation.
Start and Stop still control recording. No hands-free functionality is added.

Visual changes:
- Perfectly circular planet silhouette
- Deep matte shading and directional light
- Narrow flowing colored surface currents (less washed-out/cloudy)
- Subtle atmospheric halo, muted limb rim and breathing
- Same activity colors, with red for Error
- Uses Qt raster painting and numpy; no OpenGL dependency.

Notes: Python syntax and ZIP integrity validated; actual Windows visual
rendering and audio integration have not been tested in this environment.
