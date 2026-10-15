"""Deliberately small, auditable allowlist of safe Windows commands."""

import re
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class Intent:
    name: str
    target: str = ""


# Keep the parser strict: never allow 'do X and dangerous Y' to run just X.
_APP_NAMES = {
    "notepad": "notepad",
    "calculator": "calculator",
    "file explorer": "explorer",
    "explorer": "explorer",
    "chrome": "chrome",
    "google chrome": "chrome",
    "vs code": "vscode",
    "visual studio code": "vscode",
}
_FOLDER_NAMES = {
    "downloads": "Downloads",
    "documents": "Documents",
    "desktop": "Desktop",
}


def interpret(spoken_text: str) -> Intent:
    """Parse one complete utterance; return unknown for unapproved requests."""
    text = re.sub(r"[^a-z0-9 ]", " ", spoken_text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    if text.startswith("please "):
        text = text[7:]
    if text.endswith(" please"):
        text = text[:-7]

    if text in {"help", "what can you do", "list commands", "show commands"}:
        return Intent("help")
    if text in {"what time is it", "tell me the time", "current time"}:
        return Intent("time")
    if text in {"exit artemis", "stop assistant", "quit artemis", "stop listening"}:
        return Intent("exit")

    match = re.fullmatch(r"(?:open|launch|start) (?:the |my )?(.+)", text)
    if match:
        target = match.group(1)
        target = re.sub(r" folder$", "", target)
        if target in _APP_NAMES:
            return Intent("open_app", _APP_NAMES[target])
        if target in _FOLDER_NAMES:
            return Intent("open_folder", _FOLDER_NAMES[target])

    return Intent("unknown")


def _find_program(name: str):
    if name == "chrome":
        relative = Path("Google") / "Chrome" / "Application" / "chrome.exe"
        candidates = [
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / relative,
            Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / relative,
            Path(os.environ.get("LOCALAPPDATA", "")) / relative,
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return shutil.which("chrome")
    if name == "vscode":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Microsoft VS Code" / "Code.exe",
            Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Microsoft VS Code" / "Code.exe",
        ]
        for candidate in candidates:
            if candidate.is_file():
                return str(candidate)
        return shutil.which("code")
    return None


def execute(intent: Intent) -> tuple[str, bool]:
    """Perform exactly one approved action. Return (spoken_response, should_exit)."""
    if intent.name == "help":
        return ("You can ask me to open Notepad, Calculator, Chrome, VS Code, File Explorer, Downloads, Documents or Desktop; or ask for the time.", False)
    if intent.name == "time":
        return ("The time is " + datetime.now().strftime("%I:%M %p").lstrip("0"), False)
    if intent.name == "exit":
        return ("Goodbye. ARTEMIS is no longer listening.", True)
    if intent.name == "unknown":
        return ("I did not recognize an approved command. Say help to hear the available commands.", False)

    try:
        if intent.name == "open_app":
            commands = {
                "notepad": ["notepad.exe"],
                "calculator": ["calc.exe"],
                "explorer": ["explorer.exe"],
            }
            if intent.target in commands:
                subprocess.Popen(commands[intent.target], shell=False)
                return (f"Opening {intent.target}.", False)
            if intent.target in {"chrome", "vscode"}:
                path = _find_program(intent.target)
                if not path:
                    return (f"I could not locate {intent.target}. Check whether it is installed.", False)
                subprocess.Popen([path], shell=False)
                return (f"Opening {intent.target}.", False)
        elif intent.name == "open_folder":
            # This milestone opens only named user folders; never arbitrary paths.
            if intent.target not in {"Downloads", "Documents", "Desktop"}:
                return ("That folder is not on the approved list.", False)
            folder = Path.home() / intent.target
            if not folder.is_dir():
                return (f"I could not find your {intent.target} folder.", False)
            os.startfile(str(folder))  # Windows-only, no shell string interpolation
            return (f"Opening {intent.target}.", False)
    except (OSError, ValueError) as exc:
        return (f"Windows could not complete that action: {type(exc).__name__}.", False)

    return ("That action is not on the approved list.", False)
