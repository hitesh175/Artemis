# Run in a PowerShell session whose current directory is your Artemis project root.
# Downloads small.en only on first run; later launches work offline.
$env:ARTEMIS_WHISPER_MODEL = 'small.en'
$env:ARTEMIS_WHISPER_ALLOW_DOWNLOAD = '1'
& .\.venv\Scripts\python.exe .\desktop\main.py
