"""Offline, non-destructive wake-word calibration for ARTEMIS Stage 2B.

Place next to main.py. Records a short microphone sample only in memory,
tries the same audio against several Sherpa-ONNX keyword settings, and (when
present) runs a model-supplied positive control. Does not execute PC commands,
write audio files, or contact a network.
"""
import argparse
import sys
import wave
from pathlib import Path

import numpy as np


def decode_audio(sherpa_onnx, model_paths, audio, sample_rate, score, threshold):
    """Process a recorded sample with keyword spotter, returning detected strings."""
    kws = sherpa_onnx.KeywordSpotter(
        **model_paths,
        num_threads=2,
        provider="cpu",
        keywords_score=score,
        keywords_threshold=threshold,
    )
    stream = kws.create_stream()
    hits = []
    # Feed audio in approximately 100 ms increments, as in the Sherpa example.
    chunk_size = max(1, int(sample_rate * 0.1))
    padded = np.concatenate((audio, np.zeros(int(sample_rate * 0.8), dtype=np.float32)))
    for offset in range(0, padded.size, chunk_size):
        stream.accept_waveform(sample_rate, padded[offset:offset + chunk_size])
        while kws.is_ready(stream):
            kws.decode_stream(stream)
            result = kws.get_result(stream)
            if result:
                hits.append(str(result))
                kws.reset_stream(stream)
    stream.input_finished()
    while kws.is_ready(stream):
        kws.decode_stream(stream)
        result = kws.get_result(stream)
        if result:
            hits.append(str(result))
            kws.reset_stream(stream)
    return hits


def load_test_wav(path):
    """Load official model PCM WAV positive-control sample without third-party deps."""
    with wave.open(str(path), "rb") as src:
        sr, nch, width = src.getframerate(), src.getnchannels(), src.getsampwidth()
        if width != 2:
            raise ValueError("WAV is not 16-bit PCM")
        frames = np.frombuffer(src.readframes(src.getnframes()), dtype="<i2")
    if nch > 1:
        frames = frames.reshape(-1, nch).mean(axis=1)
    return frames.astype(np.float32) / 32768.0, sr


def main():
    parser = argparse.ArgumentParser(description="Test offline Artemis keyword model with one recording")
    parser.add_argument("--device", type=int, default=None, help="Input device number (optional)")
    parser.add_argument("--seconds", type=int, default=12, help="Recording duration, 6 to 30 seconds")
    args = parser.parse_args()
    if not 6 <= args.seconds <= 30:
        parser.error("--seconds must be between 6 and 30")

    try:
        import sherpa_onnx
        import sounddevice as sd
        from artemis.kws import KWS_FOLDER, paths
    except ImportError as exc:
        print(f"Missing package/module: {exc}. Use your Artemis .venv Python.")
        sys.exit(2)

    model_paths = paths(KWS_FOLDER)
    missing = [name for name, value in model_paths.items() if not Path(value).is_file()]
    if missing:
        print(f"Missing keyword model files: {missing}")
        sys.exit(2)

    keywords = Path(model_paths["keywords_file"]).read_text(encoding="utf-8").strip()
    print("Keyword tokens:", repr(keywords), flush=True)

    # Model-supplied positive control uses the bundled reference sample and
    # reference keywords, instead of assuming the Artemis phrase must work.
    sample_dir = KWS_FOLDER / "test_wavs"
    sample_keywords = sample_dir / "test_keywords.txt"
    sample_wavs = sorted(sample_dir.glob("*.wav")) if sample_dir.exists() else []
    if sample_keywords.is_file() and sample_wavs:
        control_paths = dict(model_paths, keywords_file=str(sample_keywords))
        print("\n[Model self-test] Checking bundled sample audio...")
        for sample in sample_wavs[:3]:
            try:
                audio, sr = load_test_wav(sample)
                hits = decode_audio(sherpa_onnx, control_paths, audio, sr, 1.0, 0.25)
                print(f"  {sample.name}: {hits or 'no keyword match'}")
            except Exception as exc:
                print(f"  {sample.name}: could not test ({exc})")
    else:
        print("\n[Model self-test] Official bundled samples unavailable; skipping positive control.")

    sr = 16000
    print(f"\n[Your voice] Recording {args.seconds} seconds IN MEMORY ONLY.")
    print("After 'Recording started', say 'Hey Artemis' three times, with pauses.", flush=True)
    print("Recording started...", flush=True)
    try:
        recording = sd.rec(args.seconds * sr, samplerate=sr, channels=1, dtype="float32", device=args.device)
        sd.wait()
    except Exception as exc:
        print(f"Microphone capture failed: {exc}")
        sys.exit(2)

    recording = recording.reshape(-1)
    peak = float(np.max(np.abs(recording)))
    rms = float(np.sqrt(np.mean(recording ** 2)))
    print(f"Captured audio: peak={peak:.4f}, rms={rms:.4f}")
    if peak < 0.01:
        print("Audio is unusually quiet: verify selected microphone before judging keyword recognition.")

    print("\n[Artemis keyword test] The SAME recording is used for every setting:", flush=True)
    settings = [(1.0, 0.25), (2.0, 0.25), (3.0, 0.25), (2.0, 0.15)]
    found = False
    for score, threshold in settings:
        try:
            hits = decode_audio(sherpa_onnx, model_paths, recording, sr, score, threshold)
        except Exception as exc:
            print(f"  boost={score:.1f}, threshold={threshold:.2f}: ERROR: {exc}")
            continue
        found = found or bool(hits)
        print(f"  boost={score:.1f}, threshold={threshold:.2f}: {hits or 'NO MATCH'}", flush=True)

    print("\n[Conclusion]")
    if found:
        print("At least one setting detected something. Share the matching setting and its output.")
        print("Do NOT apply a sensitive setting to always-on automation without a false-trigger test.")
    else:
        print("All combinations missed the Artemis phrase; a new wake-word model or different detector may be needed.")
    print("No microphone audio was saved, and no commands were executed.")


if __name__ == "__main__":
    main()
