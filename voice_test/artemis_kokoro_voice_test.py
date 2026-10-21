"""Standalone local voice audition. Does not modify Artemis."""
import argparse
from pathlib import Path
import time
import numpy as np
import sounddevice as sd
from kokoro_onnx import Kokoro

HERE = Path(__file__).resolve().parent
MODEL = HERE / "kokoro-v1.0.onnx"
VOICES = HERE / "voices-v1.0.bin"
OPTIONS = ["af_heart", "af_sarah", "bf_emma", "bf_isabella"]
TEXT = "Hey, I'm Artemis. Spotify is open. Anything else you'd like me to do?"

def main():
    if not MODEL.is_file() or not VOICES.is_file():
        raise SystemExit("Download kokoro-v1.0.onnx and voices-v1.0.bin into the folder containing this script first.")
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=OPTIONS + ["all"], default="all")
    args = ap.parse_args()
    print("Loading Kokoro model...")
    start = time.perf_counter()
    engine = Kokoro(str(MODEL), str(VOICES))
    print(f"Model loaded in {time.perf_counter()-start:.2f}s")
    names = OPTIONS if args.voice=="all" else [args.voice]
    for name in names:
        print(f"\n{name}: synthesizing…", flush=True)
        begin=time.perf_counter()
        samples, sr = engine.create(TEXT, voice=name, speed=1.0,
                                    lang="en-gb" if name.startswith("bf_") else "en-us")
        print(f"Synthesized in {time.perf_counter()-begin:.2f}s, playback {len(samples)/sr:.2f}s")
        sd.play(np.asarray(samples,dtype=np.float32), sr)
        sd.wait()
    print("\nDone. Choose the voice you like before integrating it into Artemis.")

if __name__=="__main__":
    main()
