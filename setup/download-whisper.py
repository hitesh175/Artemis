"""Explicit model download only; never capture or play audio."""
from faster_whisper import WhisperModel

print('Preparing the base.en Whisper cache. A model download may be required.',flush=True)
WhisperModel('base.en',device='cpu',compute_type='int8',local_files_only=False)
print('base.en is cached. No recording or playback was started.')
