Stage 7.4 Kokoro Isabella with offline Piper fallback.
1. Back up artemis/voice.py.
2. Extract this ZIP into the Artemis PROJECT ROOT, not the artemis package folder.
3. Models should be in Artemis/voice_test/: kokoro-v1.0.onnx and voices-v1.0.bin.
   Alternatively set ARTEMIS_KOKORO_DIR to the folder containing both files.
4. Install: .\.venv\Scripts\python.exe -m pip install kokoro-onnx sounddevice numpy
5. Test: .\.venv\Scripts\python.exe -m artemis.test_isabella_740
6. Launch your previously working app file (e.g. .\artemis\artemis_orb_voice_723.py).
Voice synthesis now uses Isabella by default with one clip per response. The first
response may be slower while Kokoro loads; subsequent turns reuse the model.
App execution time is not modified; synthesis still starts after the command returns.
