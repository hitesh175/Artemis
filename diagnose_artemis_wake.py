"""ARTEMIS Stage 2B diagnostic: checks microphone + Sherpa decoding, offline.

Place this file next to main.py in your Artemis project. Safe: does not
transcribe conversation, save audio, contact networks, or execute PC actions.
"""
import argparse
import time

import numpy as np

from artemis.config import SAMPLE_RATE
from artemis.kws import ArtemisKeywordDetector
from artemis.microphone import Microphone


def main():
    p = argparse.ArgumentParser(description="Diagnose ARTEMIS offline wake-word detection")
    p.add_argument("--device", type=int, default=None, help="Microphone ID from main.py --list-devices")
    p.add_argument("--seconds", type=int, default=24, help="Length of diagnostic in seconds")
    args = p.parse_args()

    if not 5 <= args.seconds <= 120:
        p.error("--seconds must be between 5 and 120")

    detector = ArtemisKeywordDetector()
    print("[OK] Keyword model loaded. No files will be written.", flush=True)
    print("Speak 'Hey Artemis' 3-4 times during the test, with a pause between each.", flush=True)
    print("A status line appears every 3 seconds. Ctrl+C stops the test.\n", flush=True)

    total_frames = 0
    total_decodes = 0
    max_peak = 0.0
    max_rms = 0.0
    raw_hits = 0
    start = time.monotonic()
    report_at = start + 3.0

    try:
        with Microphone(device=args.device) as microphone:
            while time.monotonic() - start < args.seconds:
                frame = microphone.read(timeout=1.0)
                if frame is None:
                    continue

                pcm = np.frombuffer(frame, dtype=np.int16)
                if pcm.size == 0:
                    continue
                audio = pcm.astype(np.float32) / 32768.0
                total_frames += 1
                max_peak = max(max_peak, float(np.max(np.abs(audio))))
                max_rms = max(max_rms, float(np.sqrt(np.mean(audio * audio))))

                detector.stream.accept_waveform(SAMPLE_RATE, audio)
                while detector.spotter.is_ready(detector.stream):
                    detector.spotter.decode_stream(detector.stream)
                    total_decodes += 1
                    result = detector.spotter.get_result(detector.stream)
                    if result:
                        raw_hits += 1
                        print(f"[RAW KEYWORD RESULT] {result!r}", flush=True)
                        detector.reset()

                now = time.monotonic()
                if now >= report_at:
                    print(f"[Audio/decoder] frames={total_frames}, "
                          f"decode_steps={total_decodes}, "
                          f"peak={max_peak:.4f}, "
                          f"max_rms={max_rms:.4f}, "
                          f"keyword_hits={raw_hits}", flush=True)
                    report_at = now + 3.0
                    max_peak = 0.0
                    max_rms = 0.0
    except KeyboardInterrupt:
        print("\nStopped by user.", flush=True)

    print(f"\n[Summary] frames={total_frames} decode_steps={total_decodes} "
          f"keyword_hits={raw_hits}", flush=True)
    print("If frames > 0, decode_steps > 0, and hits = 0, audio reaches the "
          "model but it is not matching the keyword.", flush=True)


if __name__ == "__main__":
    main()
