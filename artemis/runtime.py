"""ARTEMIS Stage 2: offline 'Hey Artemis' wake phrase + safe Windows actions."""
import sys
import time

from vosk import Model as VoskModel, SetLogLevel

from .commands import execute, interpret
from .config import VOSK_PATH
from .microphone import Microphone
from .speech import listen_for_command
from .voice import Speaker
from .wakeword import JarvisDetector, VoskPhraseDetector
from .kws import ArtemisKeywordDetector


def run(device=None, voice=True, wake_mode="kws", wake_debug=False, wake_test=False):
    if sys.platform != "win32":
        raise RuntimeError("ARTEMIS currently targets Windows 10/11 only.")
    if not wake_test and not VOSK_PATH.is_dir():
        raise RuntimeError("Vosk model missing. Run: .venv\\Scripts\\python.exe setup_models.py")

    SetLogLevel(-1)
    vosk_model = None
    if wake_mode == "kws":
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
        raise ValueError("wake_mode must be 'kws', 'vosk', or 'jarvis'")
    speaker = Speaker(enabled=voice and not wake_test)
    # Preload speech recognition into memory for a fast command response, but
    # never feed it standby microphone audio in 'kws' or 'jarvis' modes.
    if not wake_test and vosk_model is None:
        print("Preparing command recognizer (only used after wake activation)...")
        vosk_model = VoskModel(str(VOSK_PATH))

    if wake_test:
        print(f"[Wake test] Say '{wake_phrase}', then pause. No commands execute.")
        print("Standby is quiet; only confirmed keyword hits will print. Ctrl+C to quit.")
    else:
        print(f"ARTEMIS is listening offline. Say '{wake_phrase}', pause, then give a command.")
        print("Ctrl+C stops microphone listening; no audio is saved to files.")
    last_handled = 0.0

    with Microphone(device=device) as microphone:
        try:
            while True:
                frame = microphone.read(timeout=1.0)
                if frame is None:
                    continue
                hit = detector.process(frame)
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
                    # Do not load large STT until after the wake phrase.
                    if vosk_model is None:
                        print("Loading command speech recognition...")
                        vosk_model = VoskModel(str(VOSK_PATH))
                    microphone.flush()
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
