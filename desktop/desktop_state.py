"""Bounded, atomic local desktop state shared by the native bridge."""
import json
import os
import threading
from pathlib import Path

DEFAULTS = dict(quiet=True, speechEnabled=True, speed=100, scale=100,
                reduceMotion=False, autoSend=True)

class DesktopState:
    def __init__(self, path=None):
        self._path = Path(path) if path else Path(__file__).resolve().parent.parent / 'data' / 'desktop-state.json'
        self._lock = threading.RLock()
        self._state = dict(preferences=dict(DEFAULTS), history=[])
        if self._path.exists():
            try:
                self._state = self._validate(json.loads(self._path.read_text(encoding='utf-8')))
            except (ValueError, OSError, TypeError):
                # Keep the original file for recovery; fail silent on invalid state.
                pass

    @staticmethod
    def _validate(data):
        if not isinstance(data, dict):
            raise ValueError('Invalid saved state')
        prefs = dict(DEFAULTS)
        source = data.get('preferences', {})
        if not isinstance(source, dict):
            raise ValueError('Invalid preferences')
        for key in ('quiet', 'speechEnabled', 'reduceMotion', 'autoSend'):
            if key in source:
                if type(source[key]) is not bool:
                    raise ValueError('Invalid preference: ' + key)
                prefs[key] = source[key]
        for key, low, high in (('speed', 0, 180), ('scale', 70, 130)):
            if key in source:
                value = source[key]
                if type(value) not in (int, float) or not low <= value <= high:
                    raise ValueError('Invalid preference: ' + key)
                prefs[key] = value
        history = data.get('history', [])
        if not isinstance(history, list) or len(history) > 100:
            raise ValueError('Invalid conversation length')
        clean = []
        for item in history:
            if not isinstance(item, dict) or item.get('role') not in ('user', 'assistant'):
                raise ValueError('Invalid message')
            text = item.get('content')
            if not isinstance(text, str) or not 1 <= len(text) <= 12000:
                raise ValueError('Invalid message text')
            clean.append(dict(role=item['role'], content=text))
        return dict(preferences=prefs, history=clean)

    def load(self):
        with self._lock:
            return json.loads(json.dumps(self._state))

    def save(self, data):
        clean = self._validate(data)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_suffix('.tmp')
            try:
                tmp.write_text(json.dumps(clean, ensure_ascii=False), encoding='utf-8')
                os.replace(tmp, self._path)
            finally:
                if tmp.exists():
                    tmp.unlink()
            self._state = clean
        return self.load()
