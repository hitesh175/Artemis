"""ARTEMIS conversational Piper speech: sentence-level playback, reusable voice, text cleanup."""
from __future__ import annotations
import io, os, re, wave, threading, unicodedata
from pathlib import Path

VOICE_MODEL = Path(__file__).resolve().parents[1] / 'models' / 'voices' / 'en_GB-alba-medium.onnx'
_PIPER = None
_PIPER_CONFIG = None
_PIPER_LOCK = threading.RLock()

def spoken_text(text):
    """Clean display-oriented text for speech without changing displayed replies."""
    text = str(text or '')
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.I | re.S)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'```.*?```', ' ', text, flags=re.S)
    text = re.sub(r'\[([^]]+)\]\([^)]*\)', r'\1', text)
    text = re.sub(r'(?m)^\s*[-*•]\s+', '', text)
    text = re.sub(r'[*_`#~]+', '', text)
    # Remove pictographs/symbol emojis, emoji selectors, and joiner sequences.
    text = ''.join(ch for ch in text if not (
        unicodedata.category(ch) in ('So','Sk','Cs') or
        ch in ('\ufe0f', '\ufe0e', '\u200d', '\u20e3') or
        0x1F1E6 <= ord(ch) <= 0x1FAFF
    ))
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def speech_chunks(text, max_chars=180):
    """Use sentence boundaries, but cap long chunks to avoid large synthesis delays."""
    text = spoken_text(text)
    if not text: return []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks=[]
    for sentence in sentences:
        if len(sentence) <= max_chars:
            chunks.append(sentence)
            continue
        words=sentence.split()
        part=''
        for word in words:
            if part and len(part)+len(word)+1 > max_chars:
                chunks.append(part); part=''
            part=(part+' '+word).strip()
        if part: chunks.append(part)
    return [s for s in chunks if s]

class Speaker:
    def __init__(self, enabled=True):
        self.piper = None
        self._piper_config_cls = None
        self.engine = None
        if not enabled: return
        global _PIPER, _PIPER_CONFIG
        if VOICE_MODEL.is_file() and VOICE_MODEL.with_suffix('.onnx.json').is_file():
            try:
                with _PIPER_LOCK:
                    if _PIPER is None:
                        from piper import PiperVoice, SynthesisConfig
                        _PIPER = PiperVoice.load(str(VOICE_MODEL), use_cuda=False)
                        _PIPER_CONFIG = SynthesisConfig
                        print('[Voice] Piper Alba model loaded (cached).',flush=True)
                    self.piper = _PIPER
                    self._piper_config_cls = _PIPER_CONFIG
                return
            except Exception as exc:
                print(f'[Voice] Piper unavailable: {exc}',flush=True)
        try:
            import pyttsx3
            self.engine = pyttsx3.init(driverName='sapi5')
            self.engine.setProperty('rate',180)
        except Exception as exc:
            print(f'[Voice] SAPI unavailable: {exc}',flush=True)

    def say(self, message):
        pieces=speech_chunks(message)
        print('ARTEMIS (spoken):', ' '.join(pieces),flush=True)
        if not pieces: return
        if self.piper is not None:
            import numpy as np
            import sounddevice as sd
            chosen=os.getenv('ARTEMIS_OUTPUT_DEVICE')
            device=int(chosen) if chosen and chosen.isdigit() else (chosen or None)
            # Piper voice is reused rather than loaded for every sentence.
            with _PIPER_LOCK:
                for piece in pieces:
                    output=io.BytesIO()
                    # Slightly faster than earlier 1.12 (1.0 is normal speed).
                    cfg=self._piper_config_cls(length_scale=0.98)
                    with wave.open(output,'wb') as wav:
                        self.piper.synthesize_wav(piece,wav,syn_config=cfg)
                    output.seek(0)
                    with wave.open(output,'rb') as wav:
                        rate=wav.getframerate()
                        channels=wav.getnchannels()
                        width=wav.getsampwidth()
                        raw=wav.readframes(wav.getnframes())
                    if width!=2: raise RuntimeError('Piper returned unsupported WAV sample format')
                    audio=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768.0
                    if channels>1: audio=audio.reshape(-1,channels)
                    if not len(audio): raise RuntimeError('Piper returned empty audio')
                    sd.play(audio, samplerate=rate, device=device,blocking=True)
                    sd.stop()
            return
        if self.engine is not None:
            for piece in pieces:
                self.engine.say(piece)
            self.engine.runAndWait()
