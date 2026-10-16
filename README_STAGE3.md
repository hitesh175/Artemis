# ARTEMIS Stage 3 — trained 'Hey Artemis' openWakeWord model

This is a **patch for your existing Stage 2B project**; back up the existing folder and **extract into its root**, so that `main.py` and the `artemis/` directory are overwritten. Your existing `.venv`, `models/`, Vosk transcription, and text commands remain unchanged.

## 1. Train in Google Colab (no real voice uploaded)

Recommended community-maintained 2026 trainer (third party, **not** an official openWakeWord notebook):
https://colab.research.google.com/github/alfiedennen/openwakeword-colab-2026/blob/main/train_wakeword.ipynb

Official openWakeWord docs: https://github.com/dscripka/openWakeWord#training-new-models
The official older notebook can fail on 2026 Colab dependencies. Review notebook code before executing; Colab runs downloaded training code in Google's cloud.

- In Colab: Runtime > Change runtime type > T4 GPU (if available).
- In configuration cell documented by the notebook, replace the two editable values with:

  `TARGET_PHRASE = ['hey artemis']`

  `MODEL_NAME = 'hey_artemis'`

- Optionally listen to a synthetic sample if provided and check pronunciation.
- Run `Runtime > Run all` and wait. Expect significant downloads and potentially a long run or free-tier disconnect. Do **not** upload real microphone recordings.
- Download generated `hey_artemis.onnx`. Training does not occur on your PC.

Alternatively see https://github.com/saintpete/openwakeword-colab-toolkit; for this trainer, edit **all** `hey_clem` filename/path references in the notebook as well as the YAML config (the final export is hard-coded), or use the first trainer above to avoid that error.

## 2. Copy the trained model to Windows

Place `hey_artemis.onnx` here:

    C:\Users\kanag\Desktop\Artemis\models\wakewords\hey_artemis.onnx

If your Colab export contains `hey_artemis.onnx.data`, keep that file in the **same** directory. Don't rename the sidecar independently. Do not copy the ZIP in place of an ONNX model.

PowerShell in project root:

    New-Item -ItemType Directory -Force .\models\wakewords | Out-Null
    Copy-Item "$env:USERPROFILE\Downloads\hey_artemis.onnx" .\models\wakewords\hey_artemis.onnx
    Test-Path .\models\wakewords\hey_artemis.onnx

The last command must say True. If there is a sidecar, copy it as well:

    Copy-Item "$env:USERPROFILE\Downloads\hey_artemis.onnx.data" .\models\wakewords\hey_artemis.onnx.data

(The sidecar step applies only when the model download contains that file.)

## 3. Verify local installation

Stage 1 already installed `openwakeword`. Check:

    .\.venv\Scripts\python.exe -c "import openwakeword; print('openWakeWord is installed')"

If that fails, install requirements as previously:

    .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Run command parser tests:

    .\.venv\Scripts\python.exe -m unittest discover -s tests -v

## 4. Safe wake-word test — no Windows actions

    .\.venv\Scripts\python.exe main.py --wake-test --wake-debug

Speak 'Hey Artemis' 10 times, with pauses. The optional score display prints only numeric scores, **not** conversations. It never executes system commands. Start threshold 0.50.

If it does not trigger but scores increase, test a lower threshold (0.40) only **after** measuring background false activations:

    .\.venv\Scripts\python.exe main.py --wake-test --wake-debug --wake-threshold 0.40

A high false alarm rate means retrain or increase threshold (0.60+), not decrease it.

## 5. False-activation testing

Leave `--wake-test` running for at least 30–60 minutes in normal ambient noise. The assistant must not activate on normal speech or video audio. Then try 20 deliberate wake phrases; a practical preliminary target is at least 16/20 detections and no triggers during the 30–60 minute background test. Longer evaluation is recommended before daily deployment; this test does not guarantee security.

Only once you're happy with wake-test results, enable the assistant:

    .\.venv\Scripts\python.exe main.py

Speak 'Hey Artemis', pause, then 'Open Notepad'. All commands still use the existing strict allowlist. There is no AI execution of arbitrary commands. Voice is **not** speaker authentication.

## Troubleshooting

- `.onnx` cannot load: missing `.onnx.data`, incomplete Colab export, or incompatible ONNX opset/runtime. Keep exact exported files together.
- No activation: confirm model file and test raw score trace. If near zero for your pronunciation, retrain using more varied synthetic voices/pronunciations. Don't lower the threshold blindly.
- Windows runtime installs with `openwakeword>=0.6.0,<0.8` as Stage 1. The Colab training stack is separate from your local Python 3.11 virtual environment.
- You can still use `main.py --text` while debugging. No model file is needed in text mode.
- To return to earlier detector for comparison: `main.py --wake-mode kws --wake-test` or `--wake-mode jarvis --wake-test`.
- Privacy: the model was trained with synthetic speech in Google Colab, but Colab still involves Google infrastructure and downloading third-party code and data. Normal Artemis wake detection and speech recognition run locally; don't upload personal recordings to Colab.
- Licensing: check training-data/model licenses before commercial use. Some sources may be noncommercial-only.
