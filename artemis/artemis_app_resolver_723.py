"""Local Windows Start Menu shortcut discovery and conservative app name matching.
Only shortcut files inside known Start Menu/Desktop directories may be launched.
No arbitrary shell command interpretation and no LLM-generated process execution.
"""
from __future__ import annotations
import difflib
import os
import re
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Candidate:
    name: str
    shortcut: Path
    app_id: str | None = None  # Windows registered application identifier

@dataclass(frozen=True)
class Match:
    kind: str  # exact | confirm | unknown
    app: Candidate | None = None
    score: float = 0.0

_STOP = {'app', 'application', 'desktop', 'shortcut', 'windows', 'launch', 'open', 'start', 'run', 'please', 'the'}

def key(text: str) -> str:
    return ' '.join(w for w in re.findall(r'[a-z0-9]+', text.casefold()) if w not in _STOP)

def shortcut_roots() -> list[Path]:
    roots = [Path(os.environ.get('APPDATA', '')) / 'Microsoft/Windows/Start Menu/Programs',
             Path(os.environ.get('PROGRAMDATA', '')) / 'Microsoft/Windows/Start Menu/Programs',
             Path(os.environ.get('USERPROFILE', '')) / 'Desktop',
             Path(os.environ.get('PUBLIC', '')) / 'Desktop']
    return [p.resolve() for p in roots if p.is_dir()]

def discover_apps() -> list[Candidate]:
    apps: dict[str, Candidate] = {}
    for root in shortcut_roots():
        try:
            for shortcut in root.rglob('*.lnk'):
                if not shortcut.is_file():
                    continue
                name = shortcut.stem.strip()
                k = key(name)
                if k and k not in apps:
                    apps[k] = Candidate(name, shortcut.resolve())
        except (PermissionError, OSError):
            continue
    # Some installed apps (especially Spotify from Microsoft Store) are
    # registered with Windows but have no discoverable .lnk file.
    # Get-StartApps returns only Windows-registered app IDs, not shell commands.
    try:
        result = subprocess.run(
            ['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
             'Get-StartApps | Select-Object Name,AppID | ConvertTo-Json -Compress'],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=12, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        if result.returncode == 0 and result.stdout.strip():
            entries = json.loads(result.stdout.lstrip('\ufeff'))
            if isinstance(entries, dict):
                entries = [entries]
            for entry in entries:
                name = str(entry.get('Name') or '').strip()
                app_id = str(entry.get('AppID') or '').strip()
                k = key(name)
                if k and app_id and k not in apps:
                    apps[k] = Candidate(name, Path(), app_id)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass  # Shortcut discovery still works if PowerShell is unavailable.
    return sorted(apps.values(), key=lambda a: a.name.casefold())

def match_app(spoken_name: str, apps: list[Candidate]) -> Match:
    wanted = key(spoken_name)
    if not wanted or len(wanted) < 2:
        return Match('unknown')
    indexed = [(a, key(a.name)) for a in apps]
    exact = [a for a, k in indexed if wanted == k]
    if len(exact) == 1:
        return Match('exact', exact[0], 1.0)
    if len(exact) > 1:
        return Match('confirm', exact[0], 1.0)
    ranked = sorted(((difflib.SequenceMatcher(None, wanted, k).ratio(), a)
                     for a, k in indexed if k), key=lambda v: v[0], reverse=True)
    if not ranked or ranked[0][0] < 0.68:
        return Match('unknown')
    # Never auto-run fuzzy matches. Explicit confirmation is always required.
    return Match('confirm', ranked[0][1], ranked[0][0])

def parse_open_request(raw: str) -> str | None:
    """Find explicit app-launch requests despite harmless leading ASR noise.

    This does NOT grant permission to launch anything: application matching,
    installation discovery, and the user's execution checkbox remain mandatory.
    """
    s = re.sub(r"\s+", " ", raw).strip()
    s = re.sub(r"^(?:(?:hey\s+)?artemis)[,.:!? ]+", "", s, flags=re.I)

    # Instructional questions are not requests to perform an action.
    # Check the full utterance BEFORE extracting an embedded "open" verb.
    question_patterns = (
        r"\bhow\s+(?:do|can|would|should)\s+(?:i|we|you)\s+(?:go\s+about\s+)?(?:open|launch|start|run)\b",
        r"\b(?:could|can)\s+you\s+(?:tell|show|explain)\s+(?:me\s+)?how\s+to\s+(?:open|launch|start|run)\b",
        r"\b(?:what(?:'s|\s+is)\s+the\s+(?:way|best\s+way)\s+to)\s+(?:open|launch|start|run)\b",
        r"\b(?:how\s+to|tell\s+me\s+how\s+to|explain\s+how\s+to)\s+(?:open|launch|start|run)\b",
    )
    if any(re.search(pattern, s, flags=re.I) for pattern in question_patterns):
        return None

    # Look for an explicit action verb even if Whisper prefixed extra words.
    # Restrict target to the immediate short phrase, not a whole conversation.
    # A question about HOW to open an app is not an instruction to open it.
    if re.search(r"\b(?:how\s+to|tell\s+me\s+how\s+to|explain\s+how\s+to)\s+(?:open|launch|start|run)\b", s, re.I):
        return None
    verb = re.search(r"\b(?:open|launch|start|run)\s+", s, flags=re.I)
    if verb:
        suffix = s[verb.end():]
    else:
        # Whisper can merge the verb with the target: "OpenSpartify".
        # Only accept an action verb stuck to the START of a short token;
        # keep fuzzy application matches behind user confirmation.
        joined = re.search(r"\b(?:open|launch|start)([A-Za-z][A-Za-z0-9]{2,30})\b", s, re.I)
        if not joined:
            return None
        suffix = joined.group(1)
    suffix = re.split(r"[.!?;,]", suffix, maxsplit=1)[0]
    suffix = re.split(r"\s+(?:and\s+then|then|because|so\s+that)\b", suffix,
                      maxsplit=1, flags=re.I)[0]
    suffix = re.sub(r"\s+(?:please|for\s+me|right\s+now)\s*$", "", suffix, flags=re.I)
    target = suffix.strip(' .?!,')
    if not target or len(target.split()) > 5:
        return None
    return target


def launch_shortcut(app: Candidate) -> None:
    if app.app_id:
        # Launch only an AppID obtained from Windows discovery, never raw
        # transcribed text or an LLM-generated command.
        if not any(a.app_id == app.app_id for a in discover_apps()):
            raise PermissionError('Application is no longer registered with Windows.')
        subprocess.Popen(['explorer.exe', 'shell:AppsFolder\\' + app.app_id])
        return
    path = app.shortcut.resolve(strict=True)
    if path.suffix.casefold() != '.lnk' or not any(path.is_relative_to(root) for root in shortcut_roots()):
        raise PermissionError('Shortcut is outside the approved application directories.')
    os.startfile(str(path))  # Windows only; shell executes an existing Start Menu shortcut
