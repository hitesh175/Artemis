"""ARTEMIS Stage 2: offline 'Hey Artemis' wake phrase + safe Windows actions."""
import sys
import time

from vosk import Model as VoskModel, SetLogLevel

from .commands import execute, interpret
from .config import VOSK_PATH
from .microphone import Microphone
from .speech import listen_for_command
from .speech_whisper import listen_for_whisper_command
from .voice import Speaker
from .wakeword import JarvisDetector, VoskPhraseDetector
from .kws import ArtemisKeywordDetector
from .oww_custom import ArtemisOpenWakeWordDetector


def run(device=None, voice=True, wake_mode="oww", wake_debug=False, wake_test=False,
        wake_threshold=0.50, stt="whisper", whisper_model_name="base.en", whisper_device="cpu"):
    if sys.platform != "win32":
        raise RuntimeError("ARTEMIS currently targets Windows 10/11 only.")
    if not wake_test and stt == "vosk" and not VOSK_PATH.is_dir():
        raise RuntimeError("Vosk model missing. Run: .venv\\Scripts\\python.exe setup_models.py")

    SetLogLevel(-1)
    vosk_model = None
    if wake_mode == "oww":
        print("Loading trained Hey Artemis openWakeWord model (offline)...")
        detector = ArtemisOpenWakeWordDetector(threshold=wake_threshold)
        wake_phrase = "Hey Artemis"
    elif wake_mode == "kws":
        print("Loading local Artemis keyword spotter (no standby transcription)...")
        detector = ArtemisKeywordDetector()
        wake_phrase = "Hey Artemis"
    elif wake_mode == "vosk":
        if not VOSK_PATH.is_dir():
            raise RuntimeError("Vosk model missing. Run: .venv\\Scripts\\python.exe setup_models.py")
        print("Loading the legacy Vosk wake-phrase recognizer...")
        vosk_model = VoskModel(str(VOSK_PATH))
        detector = VoskPhraseDetector(vosk_model, debug=wake_debug)
        wake_phrase = "Hey Artemis"
    elif wake_mode == "jarvis":
        detector = JarvisDetector(debug=wake_debug)
        wake_phrase = "Hey Jarvis"
    else:
        raise ValueError("wake_mode must be 'oww', 'kws', 'vosk', or 'jarvis'")
    speaker = Speaker(enabled=voice and not wake_test)
    # The ASR model stays loaded, but receives audio only AFTER a wake hit.
    whisper_model = None
    if not wake_test:
        if stt == "whisper":
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError("faster-whisper missing; install with: python -m pip install faster-whisper") from exc
            compute_type = "int8" if whisper_device == "cpu" else "float16"
            print(f"Loading offline faster-whisper model ({whisper_model_name}, {whisper_device})...", flush=True)
            try:
                whisper_model = WhisperModel(whisper_model_name, device=whisper_device,
                                             compute_type=compute_type, local_files_only=True)
            except Exception as exc:
                raise RuntimeError(
                    "Could not load cached Whisper model. If missing, run: "
                    ".venv\\Scripts\\python.exe main.py --prepare-whisper; "
                    "for CUDA errors, try --whisper-device cpu. "
                    f"Original error: {type(exc).__name__}: {exc}"
                ) from exc
        elif stt == "vosk":
            if vosk_model is None:
                print("Preparing Vosk command recognizer (only used after wake activation)...")
                vosk_model = VoskModel(str(VOSK_PATH))
        else:
            raise ValueError("stt must be 'whisper' or 'vosk'")

    if wake_test:
        print(f"[Wake test] Say '{wake_phrase}', then pause. No commands execute.")
        print("Standby is quiet; only confirmed keyword hits will print. Ctrl+C to quit.")
    else:
        print(f"ARTEMIS is listening offline. Say '{wake_phrase}', pause, then give a command.")
        print("Ctrl+C stops microphone listening; no audio is saved to files.")
    last_handled = 0.0
    last_score_report = time.monotonic()

    with Microphone(device=device) as microphone:
        try:
            while True:
                frame = microphone.read(timeout=1.0)
                if frame is None:
                    continue
                hit = detector.process(frame)
                # An optional confidence trace, not speech-to-text. Never saves audio.
                if wake_debug and wake_mode == "oww":
                    now = time.monotonic()
                    if now - last_score_report >= 2.0:
                        print(f"[Wake score] peak={detector.top_score:.3f} "
                              f"threshold={wake_threshold:.2f}")
                        detector.top_score = 0.0
                        last_score_report = now
                if hit is None:
                    continue

                # Wake test never launches any apps. It's a safe diagnostic.
                if wake_test:
                    print(f"[Wake test SUCCESS] Recognized '{wake_phrase}'.")
                    detector.reset()
                    continue

                if time.monotonic() - last_handled < 2.0:
                    continue
                print(f"[Wake detected] {wake_phrase}")
                if hit.command_tail:
                    command_text = hit.command_tail
                else:
                    print("[Listening for command...]")
                    microphone.flush()
                    if stt == "whisper":
                        command_text = listen_for_whisper_command(microphone, whisper_model)
                    else:
                        command_text = listen_for_command(microphone, vosk_model)

                if not command_text:
                    reply, should_exit = "I did not hear a command. Please try again.", False
                else:
                    print(f"You: {command_text}")
                    reply, should_exit = execute(interpret(command_text))
                speaker.say(reply)

                # Prevent stale queued microphone audio and voice playback
                # from being interpreted as a new wake phrase.
                microphone.flush()
                detector.reset()
                last_handled = time.monotonic()
                if should_exit:
                    break
                print(f"[Standby] Say '{wake_phrase}'")
        except KeyboardInterrupt:
            print("\nARTEMIS stopped. Microphone released.")
