"""Quick Artemis speaker diagnostic (does not need microphone or Ollama)."""
from artemis.voice import Speaker
v = Speaker(enabled=True)
print('Piper available:', getattr(v, 'piper', None) is not None)
print('Windows SAPI available:', getattr(v, 'engine', None) is not None)
if getattr(v, 'piper', None) is None and getattr(v, 'engine', None) is None:
    raise RuntimeError('No working TTS backend. Try: python -m pip install pyttsx3')
v.say('Hello. Artemis speech test. Can you hear me?')
print('Voice test completed. If silent, check Windows output device and volume.')
