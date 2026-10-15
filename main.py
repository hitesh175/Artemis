"""ARTEMIS Windows entry point. Run main.py --help for options."""
import argparse


def main():
    parser = argparse.ArgumentParser(description="ARTEMIS: offline voice + safe PC commands")
    parser.add_argument("--device", type=int, default=None, help="Microphone index (see --list-devices)")
    parser.add_argument("--list-devices", action="store_true", help="List microphones")
    parser.add_argument("--no-voice", action="store_true", help="Print responses instead of speaking")
    parser.add_argument("--text", action="store_true", help="Run text command test without microphone")
    parser.add_argument("--wake-mode", choices=("kws", "vosk", "jarvis"), default="kws",
                        help="kws uses custom offline keyword spotting (recommended); vosk is legacy STT fallback; jarvis uses pretrained Hey Jarvis")
    parser.add_argument("--wake-debug", action="store_true",
                        help="Display live wake recognizer transcripts in terminal (privacy-sensitive)")
    parser.add_argument("--wake-test", action="store_true",
                        help="Test wake phrase recognition WITHOUT executing Windows commands")
    args = parser.parse_args()

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
        wake_test=args.wake_test)


if __name__ == "__main__":
    main()
