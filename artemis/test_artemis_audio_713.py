"""ARTEMIS audio diagnostic; run as python -m artemis.test_artemis_audio_713 from project root."""
import os
import numpy as np
import sounddevice as sd
from artemis.voice import Speaker

print('Default devices (input, output):', sd.default.device)
print('Available output devices:')
for i, d in enumerate(sd.query_devices()):
    if d['max_output_channels']:
        print(f"  {i}: {d['name']} (outputs={d['max_output_channels']}, default Hz={d['default_samplerate']})")

print('\nChecking direct output with a short tone...')
rate = 44100
x = np.arange(int(rate*.35), dtype=np.float32) / rate
tone = (.12*np.sin(2*np.pi*440*x)).astype('float32')
chosen = os.environ.get('ARTEMIS_OUTPUT_DEVICE')
device = int(chosen) if chosen and chosen.isdigit() else (chosen or None)
try:
    sd.play(tone, samplerate=rate, blocking=True, device=device)
    sd.stop()
    print('Direct test tone sent to device successfully.')
except Exception as e:
    print(f'Direct sounddevice test failed: {type(e).__name__}: {e}')

print('\nChecking Piper...')
Speaker(enabled=True).say('Hello. This is Artemis. Can you hear my voice now?')
print('Audio diagnostic finished. If the tone or voice is silent, verify Windows output routing.')
