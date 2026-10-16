"""ARTEMIS Windows entry point. Run main.py --help for options."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="ARTEMIS: offline voice + safe PC commands")
    parser.add_argument("--device", type=int, default=None, help="Microphone index (see --list-devices)")
    parser.add_argument("--list-devices", action="store_true", help="List microphones")
    parser.add_argument("--no-voice", action="store_true", help="Print responses instead of speaking")
    parser.add_argument("--text", action="store_true", help="Run text command test without microphone")
    parser.add_argument("--wake-mode", choices=("oww", "kws", "vosk", "jarvis"), default="oww",
                        help="oww uses trained Hey Artemis ONNX model; kws is the older Sherpa method; vosk is legacy STT; jarvis is the original pretrained fallback")
    parser.add_argument("--wake-threshold", type=float, default=0.50,
                        help="openWakeWord activation threshold (default 0.50)")
    parser.add_argument("--wake-debug", action="store_true",
                        help="Display live wake recognizer transcripts in terminal (privacy-sensitive)")
    parser.add_argument("--stt", choices=("whisper", "vosk"), default="whisper",
                        help="Command transcription backend (default: whisper; Vosk fallback available)")
    parser.add_argument("--whisper-model", default="base.en",
                        help="Cached faster-whisper model (default: base.en; try small.en for higher accuracy)")
    parser.add_argument("--whisper-device", choices=("cpu", "cuda"), default="cpu",
                        help="CPU (most compatible) or CUDA (requires Windows CUDA/cuDNN DLLs)")
    parser.add_argument("--prepare-whisper", action="store_true",
                        help="Download/cache Whisper model once, then exit; requires Internet for initial download")
    parser.add_argument("--wake-test", action="store_true",
                        help="Test wake phrase recognition WITHOUT executing Windows commands")
    args = parser.parse_args()

    if args.prepare_whisper:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise SystemExit("Install first: .venv\\Scripts\\python.exe -m pip install faster-whisper") from exc
        compute_type = "int8" if args.whisper_device == "cpu" else "float16"
        print(f"Downloading/caching {args.whisper_model} for {args.whisper_device} (first time only)...", flush=True)
        WhisperModel(args.whisper_model, device=args.whisper_device, compute_type=compute_type)
        print("Whisper model cached. ARTEMIS can now transcribe locally/offline.")
        return

    if args.list_devices:
        import sounddevice as sd
        print(sd.query_devices())
        return
    if args.text:
        from artemis.commands import interpret, execute
        print("ARTEMIS text mode. Commands restricted. Type 'exit artemis' to quit.")
        while True:
            try:
                command = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            reply, should_exit = execute(interpret(command))
            print("ARTEMIS:", reply)
            if should_exit:
                break
        return

    from artemis.runtime import run
    run(device=args.device, voice=not args.no_voice,
        wake_mode=args.wake_mode, wake_debug=args.wake_debug,
        wake_test=args.wake_test, wake_threshold=args.wake_threshold,
        stt=args.stt, whisper_model_name=args.whisper_model, whisper_device=args.whisper_device)


if __name__ == "__main__":
    main()
