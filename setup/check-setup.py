"""Read-only setup status; never capture, synthesize or play audio."""
import json
from pathlib import Path
from windows_setup import readiness

print(json.dumps(readiness(Path(__file__).resolve().parents[1]),indent=2))
