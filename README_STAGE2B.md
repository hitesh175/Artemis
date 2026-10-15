# ARTEMIS Stage 2B — quiet, offline keyword spotting

This patch changes the DEFAULT wake detector from continuous Vosk transcription to **Sherpa-ONNX** open-vocabulary keyword spotting for `HEY ARTEMIS`. Unlike full STT, it doesn't produce a running transcript of everyday speech. It processes microphone audio in memory to spot a keyword; it is not speaker authentication and can still activate if a person or recording says the wake phrase. **No microphone, Windows, or real-world wake-word tests have been run in the build environment** — start in the safe wake-test mode.

The built-in English GigaSpeech keyword spotting model supports arbitrary keyword phrases using tokenization without training a new model. This is still an acoustic model: its true false-activation and recognition rates must be measured on your microphone.

### Installation into existing Windows Artemis project

1. Stop running Artemis using `Ctrl+C`. Back up your Artemis project folder.
2. Download **ARTEMIS_stage2b_keyword_patch.zip** to Downloads.
3. In VS Code, open your existing `C:\Users\kanag\Desktop\Artemis` folder, the one containing `main.py` and `.venv`.
4. Paste **exactly**:

   ```powershell
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ARTEMIS_stage2b_keyword_patch.zip" -DestinationPath . -Force
   ```

   The archive contains only changed/new files; your existing models, `.venv`, `artemis/commands.py`, and other source files remain intact.

5. Install the new keyword spotter:

   ```powershell
   .\.venv\Scripts\python.exe -m pip install -r requirements_stage2b.txt
   ```

6. Fetch the English model and generate the keyword locally (requires internet once):

   ```powershell
   .\.venv\Scripts\python.exe setup_keyword_model.py
   ```

7. Test without any PC automation:

   ```powershell
   .\.venv\Scripts\python.exe main.py --wake-test
   ```

   While quiet or while another person is speaking, the console should print **nothing**. Say `Hey Artemis` and pause: look for `[Wake test SUCCESS] Recognized 'Hey Artemis'`. If the test misses it, try three to five repetitions, a quiet room, and a different input microphone using `--list-devices` and `--device N`. Press Ctrl+C to end. The model is *not guaranteed* to recognize this phrase on your hardware without threshold/acoustic tuning.

8. Only if wake-test works reliably:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```

   Say `Hey Artemis`, pause, then `open Notepad`. Command recognition is preloaded into RAM but will not analyze audio until the wake keyword has been detected.

### Notes and recovery

- `--text` still works, without either speech model.
- Default wake mode is `--wake-mode kws`.
- `--wake-mode vosk --wake-test --wake-debug` is available as an *optional* diagnostic fallback, but it DOES create local temporary transcripts. The patch fixes the earlier bug that showed debug transcripts even when `--wake-debug` was omitted.
- `--wake-mode jarvis` still works if the old trained Jarvis model is installed.
- Normal command recognition with Vosk runs only after the keyword detector fires. There is no full-speech transcription during standby.
- The microphone is *still active* in standby for sound pattern matching; pressing Ctrl+C stops it. The system does not upload audio or store it as a file.
- In the test mode, *no Windows automation executes.*
- Accuracy is not yet measured. If the model struggles with your pronunciation/accent or yields false positives, we can tune keyword threshold or eventually train a dedicated Artemis model.
- For safety, don't enable sensitive command automation until you have tested false activations in realistic conditions. This patch does not add any new PC actions.

### Official technical references

- Sherpa-ONNX keyword spotting: https://k2-fsa.github.io/sherpa/onnx/kws/index.html
- English model and keyword token generation: https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html
- Python microphone keyword spotting example: https://github.com/k2-fsa/sherpa-onnx/blob/master/python-api-examples/keyword-spotter-from-microphone.py
