# ARTEMIS Stage 4 – faster-whisper offline commands (Windows)

Replaces **Vosk command transcription** with **faster-whisper**; preserves the custom Hey Artemis openWakeWord detector, command allowlist, and spoken Windows SAPI5 feedback. No personal audio is uploaded or saved. The model must be downloaded once.

## Install into an existing Stage 3 project

From `C:\Users\kanag\Desktop\Artemis` in PowerShell:

```powershell
Copy-Item .\main.py .\main.py.stage3.backup -Force
Copy-Item .\artemis\runtime.py .\artemis\runtime.py.stage3.backup -Force
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage4_whisper_patch.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m pip install faster-whisper
.\.venv\Scripts\python.exe main.py --prepare-whisper
.\.venv\Scripts\python.exe main.py --wake-threshold 0.20 --wake-debug
```

The one-time `--prepare-whisper` downloads/caches the *base.en* English model. Standard startup then uses `local_files_only=True`, so there are no cloud requests for command transcription. No audio is saved by this patch; only in-memory PCM samples are used. If the download fails, check Internet access, model hosting, and available disk space. To improve recognition, run `main.py --prepare-whisper --whisper-model small.en` once, then pass `--whisper-model small.en` during startup.

**CPU is the default** to avoid extra CUDA/cuDNN installation on Windows. CUDA accelerated faster-whisper may require matching NVIDIA CUDA/cuDNN libraries on your PATH; if you install these and confirm they work, select `--whisper-device cuda` (float16). Your custom wake-word ONNX model is unchanged.

Use `--stt vosk` to restore old behavior (requires old Vosk model). Wake testing remains `--wake-test --wake-debug --wake-threshold 0.20`; no commands run in wake-test mode.

Confirm reliable wake recognition and assess false activations before enabling additional Windows actions.
