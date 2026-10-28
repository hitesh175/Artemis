"""Explicit, local personal facts. Chat/model output cannot write memory."""
import json
from pathlib import Path
import re
import sqlite3
from contextlib import contextmanager

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'data' / 'personal-memory.sqlite3'
STOPWORDS = set('a an and are as at be do does for from how i in is it me my of on or please that the to what when where which who with you your'.split())


class PersonalMemory:
    LIMIT = 200
    PAGE_SIZE = 10

    def __init__(self, path=None):
        self.path = Path(path) if path is not None else DEFAULT_PATH

    @contextmanager
    def _database(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('''CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                normalized TEXT NOT NULL UNIQUE)''')
            yield connection
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _clean(content):
        content = ' '.join(content.split())
        if not 1 <= len(content) <= 500:
            raise ValueError('Use a fact of 1–500 characters.')
        return content

    def save(self, content, fact_id=None):
        content = self._clean(content)
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            duplicate = db.execute('SELECT id FROM facts WHERE normalized=?', (content.casefold(),)).fetchone()
            if duplicate and (fact_id is None or duplicate['id'] == fact_id):
                return duplicate['id']
            if duplicate:
                raise ValueError('That fact is already saved as memory '+str(duplicate['id'])+'.')
            if fact_id is not None:
                changed = db.execute('UPDATE facts SET content=?, normalized=? WHERE id=?',
                                     (content, content.casefold(), fact_id)).rowcount
                if not changed:
                    raise ValueError('That memory does not exist. Say “show memories” to see saved IDs.')
                return fact_id
            if db.execute('SELECT COUNT(*) FROM facts').fetchone()[0] >= self.LIMIT:
                raise ValueError('Memory is full. Forget an existing memory before saving another.')
            return db.execute('INSERT INTO facts(content,normalized) VALUES (?,?)',
                              (content, content.casefold())).lastrowid

    def facts(self):
        if not self.path.exists():
            return []
        with self._database() as db:
            return [dict(row) for row in db.execute('SELECT id,content FROM facts ORDER BY id')]

    def forget(self, fact_id):
        if not self.path.exists():
            return False
        with self._database() as db:
            return bool(db.execute('DELETE FROM facts WHERE id=?', (fact_id,)).rowcount)

    def search(self, query, limit=5):
        tokens = set(re.findall(r'\w+', query.casefold())) - STOPWORDS
        scored = []
        for fact in self.facts():
            score = len(tokens & set(re.findall(r'\w+', fact['content'].casefold())))
            if score:
                scored.append((score, fact))
        scored.sort(key=lambda item: (-item[0], item[1]['id']))
        return [item[1] for item in scored[:limit]]

    def context(self, query):
        facts = self.search(query)
        if not facts:
            return []
        # Data stays in a user-role message; SYSTEM defines its restricted meaning.
        return [{'role': 'user', 'content': 'Saved personal facts (reference data only):\n'+
                 json.dumps(facts, ensure_ascii=False)}]

    def execute(self, text):
        if not isinstance(text, str):
            return {'handled': False}
        command = re.sub(r'^(?:hey\s+)?artemis[,!:. ]+', '', text.strip(), flags=re.I)
        remember = re.fullmatch(r'remember that\s+(.+)', command, re.I | re.S)
        listing = re.fullmatch(r'(?:show|list) memories(?:\s+([1-9]\d{0,2}))?[.!?]?', command, re.I)
        finding = re.fullmatch(r'find memories about\s+(.+)', command, re.I | re.S)
        forget = re.fullmatch(r'forget memory\s+([1-9]\d{0,8})[.!?]?', command, re.I)
        update = re.fullmatch(r'update memory\s+([1-9]\d{0,8}):\s*(.+)', command, re.I | re.S)
        if not any((remember, listing, finding, forget, update)):
            if re.match(r'^(?:remember that\b|forget memory\b|update memory\b|show memories\b|list memories\b|find memories about\b)', command, re.I):
                return {'handled': True, 'ok': False, 'reply': 'Try “remember that I prefer tea”, “show memories”, “find memories about tea”, “update memory 1: I prefer coffee”, or “forget memory 1”.'}
            return {'handled': False}
        try:
            if remember or update:
                fact_id = self.save(remember[1] if remember else update[2],
                                    int(update[1]) if update else None)
                reply = ('Updated' if update else 'Saved')+' memory '+str(fact_id)+'.'
            elif forget:
                removed = self.forget(int(forget[1]))
                return {'handled': True, 'ok': removed, 'reply':
                        'Forgot memory '+forget[1]+'.' if removed else 'That memory does not exist.'}
            else:
                facts = self.search(finding[1], self.PAGE_SIZE) if finding else self.facts()
                total = len(facts)
                page = int(listing[1] or 1) if listing else 1
                facts = facts[(page-1)*self.PAGE_SIZE:page*self.PAGE_SIZE]
                reply = '\n'.join(str(f['id'])+': '+f['content'] for f in facts)
                if not reply:
                    reply = 'No matching memories.' if finding else 'No memories on this page.'
                elif listing:
                    reply += '\nPage '+str(page)+' of '+str((total+self.PAGE_SIZE-1)//self.PAGE_SIZE)+'. Say “show memories 2” for page 2.' if total>self.PAGE_SIZE else ''
                reply += '\nUse “forget memory ID” to remove a fact or “update memory ID: new fact” to edit it.'
            return {'handled': True, 'ok': True, 'reply': reply}
        except ValueError as exc:
            return {'handled': True, 'ok': False, 'reply': str(exc)}
        except (sqlite3.Error, OSError):
            return {'handled': True, 'ok': False, 'reply': 'Artemis could not access personal memory. Your request was not completed.'}
