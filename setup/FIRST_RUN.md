# Set up Artemis on Windows

## Install the application

Use Windows x64 with Python 3.11 x64 installed from
https://www.python.org/downloads/windows/.
Extract the complete Artemis source ZIP into a folder. In PowerShell, run:

```powershell
.\scripts\install-windows.ps1
```

The guided installer offers a new per-user folder under LocalAppData. It verifies
the release manifest, creates a separate Python environment, and downloads the
application packages. It refuses to overwrite an existing installation. A failed
new installation keeps its status file and can be resumed with the same release:

```powershell
.\scripts\install-windows.ps1 -Target "C:\path\to\new\Artemis" -Resume
```

No language/voice model downloads, recordings, speech, autostart or scheduled tasks
are enabled by installation. Shortcuts use the new Python environment; existing
shortcuts are never overwritten. Open Artemis.lnk inside the new folder after
completing the needed prerequisites. The guided installer does not create a new
Artemis.exe; that executable is not required for the shortcut launcher.

## Desktop display

The Microsoft Edge WebView2 Evergreen Runtime is required. Having the Edge browser
alone is not a substitute. Install the runtime from Microsoft's official page:
https://developer.microsoft.com/en-us/microsoft-edge/webview2/.
The installer reports a missing runtime and leaves installation instructions; it
does not silently install system software.

## Local conversation

Install Ollama from https://ollama.com/download/windows and start it.
You can use an existing local model through Settings → Local intelligence.
To recreate the current Artemis model definition, run these commands yourself:

```powershell
ollama pull kamekichi128/qwen3-4b-instruct-2507
ollama create artemis -f "C:\path\to\new\Artemis\Modelfile"
```

The pull can download a large model. It is not run automatically. Model weights
are not included in the source ZIP. Your new installation starts in Quiet mode
with hands-free and scheduled briefings off.

## Voice output

From the official Kokoro ONNX model release:
https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
download **kokoro-v1.0.onnx** and **voices-v1.0.bin**. Put both files in the new
installation's **models/kokoro/** directory. Keep the official filenames. The model
files are separate from the Python package and are not included in the ZIP.

## Microphone recognition model

The application uses cached base.en Whisper by default and does not automatically
download a missing model during recording. In the new installation folder, run:

```powershell
.\.venv\Scripts\python.exe setup\download-whisper.py
```

This explicitly downloads/caches base.en if needed. It does not record or play
audio. It uses the standard per-user Hugging Face model cache, which may be shared
with other applications. No microphone permission is needed for this download.

## Check readiness

Run the installed setup check without starting recording or playback:

```powershell
.\.venv\Scripts\python.exe setup\check-setup.py
```

Then open Artemis and use Settings → Service status. Voice preparation can silently
check that the cached models load. Actual microphone and speaker quality still
needs a user-initiated test. If dependencies failed to install, resume the setup
instead of assuming the app is ready. A check can identify cached model files but
does not guarantee their integrity or voice quality.

This is a guided online setup, not a self-contained/offline installer. A clean
second Windows machine is still required to establish portability. Do not copy an
existing .venv folder to another computer.
