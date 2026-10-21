"""Checks voice selection and plays one sentence; does not touch command logic."""
from artemis.voice import Speaker, find_kokoro_files, VOICE_VERSION
print(VOICE_VERSION)
print('Kokoro files:', find_kokoro_files())
s=Speaker(enabled=True)
print('Selected:', 'Isabella' if s.kokoro is not None else 'Piper fallback' if s.piper is not None else 'NONE')
s.say('Hello, I am Artemis. Spotify is open. What would you like to do next?')
