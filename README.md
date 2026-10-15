# ARTEMIS — Offline Windows Assistant (Stage 1)

**ARTEMIS is now your assistant's name. The temporary wake phrase remains "Hey Jarvis" until a custom "Hey Artemis" model is trained.** This is deliberate: the upstream openWakeWord library supplies that model. A custom "Hey Artemis" model will be a later milestone.

## What this build does

- Monitors **one microphone** while `main.py` is running, in 16 kHz/16-bit mono, 80 ms frames.
- Detects **"Hey Jarvis" locally**, then listens for your next short command.
- Converts the command to text using **Vosk locally**.
- Executes only a **fixed, explicitly approved set of commands** (no arbitrary shell, deletion, or admin operations).
- Replies using **Windows offline SAPI5 text-to-speech**, then returns to wake-word monitoring.
- Stores **no microphone recordings** and creates **no command-history log**. Terminal transcripts are visible while the app runs.
- Does **not** contact a remote service during normal use. One-time model / Python dependency setup requires internet.
- Does **not** install a background Windows service or autostart; that comes later.

This stage uses **CPU only**, with no need to install GPU/CUDA dependencies. It is not yet an LLM or screenshot-aware assistant.

## Requirements

- Windows 10/11, 64-bit **Python 3.11** (recommended), working microphone and speaker.
- At least ~200 MB free for installed voice models, plus space for Python libraries/environment.
- A working internet connection during **installation only**.

## Install — PowerShell in VS Code

Extract this folder, open it in VS Code, then open **Terminal → New Terminal**.

Check installed Python versions:

```powershell
py -0p
```

If Python 3.11 is installed, run (from this project directory):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_models.py
```

If you don't have Python 3.11, install the **Windows x64 build** from https://www.python.org/downloads/ and reopen the terminal.

**One-time setup downloads** the official Vosk 40 MB speech model and the `hey_jarvis` openWakeWord model and its ONNX feature extractors. Later launches do not download any models.

### Privacy verification tip

After model setup, disconnect Wi-Fi and run `main.py`; routine voice recognition and commands should still work. Opening Chrome does not navigate to an online site, but the Chrome application may itself use network access independently. For strict offline testing, turn off connectivity or block outbound traffic.

## Start ARTEMIS

```powershell
.\.venv\Scripts\python.exe main.py
```

Say: **"Hey Jarvis"**, pause around half a second, then say **"open Notepad"**.

You should see `[Wake word detected]`, the recognized transcript, and hear a Windows-generated spoken answer. The program returns to standby automatically.

To stop immediately, press **Ctrl+C** in the terminal. You can also say **"Hey Jarvis"**, pause, then **"stop assistant"**.

**ARTEMIS only listens while the Python program is running.** No Windows autostart is installed in Stage 1.

## Supported commands

- "Open Notepad"
- "Open Calculator"
- "Open File Explorer"
- "Open Chrome" (if Chrome executable is found)
- "Open VS Code" (if VS Code executable is found)
- "Open my Downloads folder"
- "Open Documents"
- "Open Desktop"
- "What time is it?"
- "Help"
- "Stop assistant"

One command per wake event. The strict grammar is intentional; compound commands are rejected, rather than partially executed.

## Troubleshooting

### Does not hear the microphone

1. Windows **Settings → Privacy & security → Microphone**: allow microphone access and allow desktop apps.
2. In Windows Sound Settings, select/test your microphone.
3. List available devices:

```powershell
.\.venv\Scripts\python.exe main.py --list-devices
```

4. Find the **input** device index and run:

```powershell
.\.venv\Scripts\python.exe main.py --device 1
```

Replace `1` with your own microphone's index. The microphone must support 16 kHz mono input; if it does not, choose another device. Resampling support will come later.

### Wake word is unreliable

The initial detector **only recognizes the trained phrase "Hey Jarvis"**, not "Hey Artemis". Check your microphone selection, speak clearly, use the recommended half-second pause, reduce background media noise, and adjust `WAKE_THRESHOLD` in `artemis/config.py` (default 0.55). Lower values may increase false activations.

### Commands are cut off or missed

Try pausing after the wake phrase. Change `MIC_RMS_THRESHOLD` in `artemis/config.py` if the microphone is unusually quiet/loud, and try a short command like "open Notepad". Initial Vosk transcription is lightweight, not perfect.

### No spoken reply

Run without TTS to test other components:

```powershell
.\.venv\Scripts\python.exe main.py --no-voice
```

Check Windows default speaker and volume. pyttsx3 uses your Windows SAPI voice offline.

### Test the action parser without microphone or models

```powershell
.\.venv\Scripts\python.exe main.py --text
```

### Run unit tests

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

## Safety boundaries

- No shell=True; never execute LLM-generated Python, PowerShell or CMD commands.
- Strict allowlist with named application/folder actions.
- No delete/move/modify/send/admin operations in this milestone.
- Audio buffers live only in RAM; queue bounded to ~4 seconds; no persistent recording or history.
- Voice is not identity verification. Anyone near your microphone might trigger a harmless allowlisted command.
- You must intentionally run the program. Add a clear microphone pause/stop control before any future autostart deployment.
- The console can still display spoken command transcripts (not saved as files by ARTEMIS); avoid terminal logging/recording if concerned.

## Folders

```text
ARTEMIS_offline_stage1/
├── main.py               # Run ARTEMIS; --text and --list-devices available
├── setup_models.py       # One-time model downloads
├── requirements.txt
├── artemis/
│   ├── config.py         # Tunable thresholds
│   ├── microphone.py     # 16 kHz microphone callback & bounded queue
│   ├── runtime.py        # Wake-word → command → response loop
│   ├── speech.py         # Offline Vosk STT
│   ├── commands.py       # Intent parsing and approved Windows actions
│   └── voice.py          # Offline spoken responses
└── tests/
    └── test_commands.py
```

## Next milestones

2. Dedicated custom **"Hey Artemis"** wake model; better silence/voice activity detection; Windows tray microphone toggle.
3. Smarter local speech-to-text on RTX 4060 using Faster-Whisper; local LLM intent planning with Ollama and a **separate safety policy**.
4. Screen understanding on explicit request only, richer approved automations, confirmations, and GUI.
5. Performance/battery testing, packaging, Windows sign-in start **only after** easy pause/quit controls exist.

## Upstream documentation

- https://github.com/dscripka/openWakeWord
- https://github.com/alphacep/vosk-api
- https://alphacephei.com/vosk/models
- https://python-sounddevice.readthedocs.io/
- https://github.com/nateshmbhat/pyttsx3
