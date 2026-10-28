"""ARTEMIS speech engine: Kokoro Isabella first, Piper Alba fallback.
No disk audio logs. Keeps API Speaker(enabled=True).say(reply).
"""
from __future__ import annotations
import io, os, threading, time, wave, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOICE_VERSION = '7.4 Isabella (Kokoro with Piper fallback)'
KOKORO_VOICE = 'bf_isabella'
MODEL_NAMES = ('kokoro-v1.0.onnx', 'voices-v1.0.bin')
_KOKORO = None
_PIPER = None
_PIPER_CONFIG = None
_LOAD_LOCK = threading.RLock()
_PLAY_LOCK = threading.RLock()

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
    # Remove text-based emoticons and text-style smiley labels produced by some LLMs.
    text = re.sub(r'(?<!\w)(?:[:;=8][-^]?[)(DPp]|<3)(?!\w)', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def find_kokoro_files():
    """Accept paths from the prior standalone audition or dedicated model folder."""
    options = []
    env = os.getenv('ARTEMIS_KOKORO_DIR')
    if env:
        options.append(Path(env).expanduser())
    options += [ROOT / 'voice_test', ROOT / 'models' / 'voices',
                ROOT / 'models' / 'kokoro', ROOT, Path(__file__).resolve().parent]
    for directory in options:
        paths = [directory / n for n in MODEL_NAMES]
        if all(p.is_file() for p in paths):
            return tuple(paths)
    return None


def _output_device():
    choice = os.getenv('ARTEMIS_OUTPUT_DEVICE', '').strip()
    return int(choice) if choice.isdigit() else (choice or None)


def _play(samples, rate, cancel_event=None):
    import numpy as np
    import sounddevice as sd
    audio = np.asarray(samples, dtype=np.float32)
    if not audio.size:
        raise RuntimeError('Speech engine generated empty audio')
    cancel_event = cancel_event or threading.Event()
    if audio.ndim == 1:
        audio = audio.reshape(-1, 1)
    if audio.ndim != 2:
        raise RuntimeError('Unsupported speech audio shape')
    with _PLAY_LOCK:
        if cancel_event.is_set():return
        # Own the stream: cancelling Artemis must not stop unrelated application audio.
        with sd.OutputStream(samplerate=int(rate), channels=audio.shape[1], dtype='float32',
                             device=_output_device(), blocksize=1024) as stream:
            for start in range(0, len(audio), 1024):
                if cancel_event.is_set():
                    stream.abort();return
                stream.write(audio[start:start+1024])
            if cancel_event.is_set():stream.abort()


class Speaker:
    """Keep the existing Artemis interface; no changes to working app routing."""
    def __init__(self, enabled=True):
        self.kokoro = None
        self.piper = None
        self.engine = None
        self._piper_config_cls = None
        if not enabled:
            return
        global _KOKORO, _PIPER, _PIPER_CONFIG
        files = find_kokoro_files()
        if files:
            try:
                with _LOAD_LOCK:
                    if _KOKORO is None:
                        t0 = time.perf_counter()
                        from kokoro_onnx import Kokoro
                        _KOKORO = Kokoro(str(files[0]), str(files[1]))
                        print(f'[Voice] Kokoro Isabella loaded in {time.perf_counter()-t0:.2f}s', flush=True)
                    self.kokoro = _KOKORO
                    # Older Artemis launchers check only piper/engine; this is a
                    # compatibility marker, NOT an alternative speech engine.
                    self.engine = self.kokoro
                return
            except Exception as exc:
                print(f'[Voice] Kokoro load error, trying Piper: {exc}', flush=True)
        else:
            print('[Voice] Kokoro model files not found; falling back to Piper.', flush=True)
        piper_path = ROOT / 'models' / 'voices' / 'en_GB-alba-medium.onnx'
        if piper_path.is_file() and piper_path.with_suffix('.onnx.json').is_file():
            try:
                with _LOAD_LOCK:
                    if _PIPER is None:
                        from piper import PiperVoice, SynthesisConfig
                        _PIPER = PiperVoice.load(str(piper_path), use_cuda=False)
                        _PIPER_CONFIG = SynthesisConfig
                    self.piper, self._piper_config_cls = _PIPER, _PIPER_CONFIG
                    print('[Voice] Piper Alba fallback available', flush=True)
                return
            except Exception as exc:
                print('[Voice] Piper fallback load failed:', exc, flush=True)
        # Do not disguise the absence of both requested offline engines.
        print('[Voice] Neither Kokoro nor Piper could be loaded.', flush=True)

    def say(self, message, cancel_event=None):
        cancel_event = cancel_event or threading.Event()
        if cancel_event.is_set():return
        text = spoken_text(message)
        if not text:
            return
        print(f'[Voice] {VOICE_VERSION}; engine=' + ('Kokoro' if self.kokoro else 'Piper' if self.piper else 'none'), flush=True)
        if self.kokoro is not None:
            try:
                # One clip for each answer; no stop/start gaps between sentences.
                with _LOAD_LOCK:
                    if cancel_event.is_set():return
                    start = time.perf_counter()
                    audio, rate = self.kokoro.create(text, voice=KOKORO_VOICE, speed=1.04, lang='en-gb')
                    synthesis=time.perf_counter()-start
                    print(f'[Voice] Kokoro synthesized in {synthesis:.2f}s', flush=True)
                if cancel_event.is_set():return
                playback=time.perf_counter()
                _play(audio, rate, cancel_event)
                return {'synthesis_seconds':synthesis,'playback_seconds':time.perf_counter()-playback}
            except Exception as exc:
                if cancel_event.is_set():return
                print(f'[Voice] Kokoro synthesis/playback failed: {exc}', flush=True)
                # Retry using Piper if possible, even if Kokoro initially loaded.
                self.kokoro = None
                self.engine = None
                self._enable_piper_fallback()
        if self.piper is not None:
            import numpy as np
            with _LOAD_LOCK:
                if cancel_event.is_set():return
                synthesis_start=time.perf_counter()
                out = io.BytesIO()
                cfg = self._piper_config_cls(length_scale=1.0)
                with wave.open(out, 'wb') as wav:
                    self.piper.synthesize_wav(text, wav, syn_config=cfg)
                out.seek(0)
                with wave.open(out, 'rb') as wav:
                    rate, channels, width = wav.getframerate(), wav.getnchannels(), wav.getsampwidth()
                    raw=wav.readframes(wav.getnframes())
                if width != 2:
                    raise RuntimeError('Unsupported Piper PCM format')
                audio=np.frombuffer(raw, dtype='<i2').astype(np.float32) / 32768.0
                if channels>1:
                    audio=audio.reshape(-1,channels)
                synthesis=time.perf_counter()-synthesis_start
            if cancel_event.is_set():return
            playback=time.perf_counter()
            _play(audio,rate,cancel_event)
            return {'synthesis_seconds':synthesis,'playback_seconds':time.perf_counter()-playback}
        raise RuntimeError('No offline speech engine available. Install kokoro-onnx and put both model files in voice_test.')

    def _enable_piper_fallback(self):
        global _PIPER, _PIPER_CONFIG
        p=ROOT / 'models' / 'voices' / 'en_GB-alba-medium.onnx'
        if not p.is_file() or not p.with_suffix('.onnx.json').is_file():
            return
        with _LOAD_LOCK:
            try:
                if _PIPER is None:
                    from piper import PiperVoice, SynthesisConfig
                    _PIPER=PiperVoice.load(str(p),use_cuda=False)
                    _PIPER_CONFIG=SynthesisConfig
                self.piper,self._piper_config_cls=_PIPER,_PIPER_CONFIG
            except Exception as exc:
                print(f'[Voice] Piper fallback failed: {exc}', flush=True)
