"""ARTEMIS Stage 5b: explicit push-to-talk and microphone diagnostics.

No wake word required. Audio stays in RAM; commands are preview-only unless
--execute is supplied. Uses your installed faster-whisper cache offline.
"""
import argparse
import sys
import threading
import time

import numpy as np
import sounddevice as sd

RATE = 16000


def record_until_enter(device=None):
    chunks = []
    errors = []
    max_seconds = 15
    stop = threading.Event()

    def callback(indata, frames, time_info, status):
        if status:
            errors.append(str(status))
        chunks.append(indata[:, 0].copy())

    print("Press ENTER to start speaking.", flush=True)
    input()
    print("RECORDING — say 'Open Notepad'. Press ENTER when finished.", flush=True)
    start = time.monotonic()
    with sd.InputStream(samplerate=RATE, device=device, channels=1,
                        dtype='float32', blocksize=1600, callback=callback):
        # input() blocks in the main thread; timer provides a 15-s safety cap.
        timer = threading.Timer(max_seconds, stop.set)
        timer.daemon = True
        timer.start()
        done_input = threading.Event()
        def wait_key():
            try:
                input()
            except EOFError:
                pass
            finally:
                done_input.set()
        key_thread = threading.Thread(target=wait_key, daemon=True)
        key_thread.start()
        while not stop.is_set() and not done_input.is_set():
            time.sleep(0.03)
        timer.cancel()

    if errors:
        print('Microphone notices:', errors[:3])
    if not chunks:
        return np.empty(0, dtype=np.float32)
    return np.concatenate(chunks)


def main():
    parser = argparse.ArgumentParser(description="ARTEMIS local microphone and push-to-talk diagnostic")
    parser.add_argument('--list-devices', action='store_true', help='List Windows input devices')
    parser.add_argument('--device', type=int, default=None, help='Choose input device index')
    parser.add_argument('--model', default='base.en', help='Already-cached faster-whisper model')
    parser.add_argument('--execute', action='store_true', help='Execute recognized APPROVED commands; default previews only')
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        print('Default input device index:', sd.default.device[0])
        return

    print('Input device:', sd.query_devices(args.device, 'input')['name'])
    print('Artemis push-to-talk: no wake word, no recordings saved.')
    print('Commands are PREVIEW ONLY.' if not args.execute else 'APPROVED command execution ENABLED.')

    audio = record_until_enter(args.device)
    if audio.size == 0:
        print('No microphone audio received.')
        return
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio ** 2)))
    print(f'[Mic] {audio.size/RATE:.1f}s; peak={peak:.4f}; RMS={rms:.4f}')
    if peak < 0.01:
        print('Very quiet microphone signal. Check Windows Sound > Input and selected device.')
        return
    if peak >= 0.99:
        print('Warning: microphone may be clipping; reduce Windows input volume.')

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(args.model, device='cpu', compute_type='int8', local_files_only=True)
    except Exception as e:
        print('Cannot load cached local Whisper model:', e)
        print('Try the Stage 4 --prepare-whisper option for your chosen model.')
        return

    print('[Whisper] Transcribing offline...', flush=True)
    segments, info = model.transcribe(audio, language='en', beam_size=5,
        vad_filter=True, condition_on_previous_text=False,
        without_timestamps=True)
    raw = ' '.join(s.text.strip() for s in segments).strip()
    print('[Whisper heard]:', repr(raw))
    if not raw:
        print('No speech transcribed. Try closer to the laptop microphone.')
        return

    from artemis.commands import interpret, execute
    from artemis.streaming_command import remove_wake_phrase
    command = remove_wake_phrase(raw)
    print('[Command candidate]:', repr(command))
    if not args.execute:
        print('PREVIEW ONLY — no Windows command executed. Add --execute to enable approved commands.')
        return
    reply, should_exit = execute(interpret(command))
    print('ARTEMIS:', reply)
    try:
        from artemis.voice import Speaker
        Speaker(enabled=True).say(reply)
    except Exception as e:
        print('Voice output unavailable:', type(e).__name__, str(e))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped. Microphone released.')
