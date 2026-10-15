"""Offline Windows SAPI5 spoken feedback, or terminal-only fallback."""


class Speaker:
    def __init__(self, enabled=True):
        self.engine = None
        if enabled:
            try:
                import pyttsx3
                self.engine = pyttsx3.init(driverName="sapi5")
                self.engine.setProperty("rate", 175)
            except Exception as exc:
                print(f"[Speech disabled: {type(exc).__name__}: {exc}]")

    def say(self, message: str):
        print(f"ARTEMIS: {message}")
        if self.engine is not None:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as exc:
                print(f"[TTS error: {type(exc).__name__}; falling back to text]")
                self.engine = None
