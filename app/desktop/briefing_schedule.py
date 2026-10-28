"""Opt-in daily briefing snapshots, checked only while the desktop is running."""
from contextlib import contextmanager
from datetime import datetime
import json
from pathlib import Path
import re
import sqlite3

DEFAULT_PATH=Path(__file__).resolve().parents[1]/'data'/'briefing-schedule.sqlite3'


class BriefingSchedule:
    def __init__(self,briefing,path=None,now=None):
        self._briefing=briefing
        self.path=Path(path) if path is not None else DEFAULT_PATH
        self._now=now or (lambda:datetime.now().astimezone())

    @contextmanager
    def _database(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=20);db.row_factory=sqlite3.Row
        try:
            db.execute('''CREATE TABLE IF NOT EXISTS schedule (
                id INTEGER PRIMARY KEY CHECK(id=1), enabled INTEGER NOT NULL,
                at TEXT NOT NULL,last_date TEXT,pending TEXT)''')
            db.execute("INSERT OR IGNORE INTO schedule(id,enabled,at) VALUES (1,0,'09:00')")
            db.commit()
            yield db
            db.commit()
        finally:db.close()

    @staticmethod
    def _view(row):
        return {'enabled':bool(row['enabled']),'time':row['at'],'last_date':row['last_date'],
                'pending':json.loads(row['pending']) if row['pending'] and row['enabled'] else None}

    def get(self):
        if not self.path.exists():return {'enabled':False,'time':'09:00','last_date':None,'pending':None}
        with self._database() as db:
            return self._view(db.execute('SELECT * FROM schedule WHERE id=1').fetchone())

    def configure(self,enabled,at):
        if type(enabled) is not bool or not isinstance(at,str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',at):
            raise ValueError('Choose whether scheduling is enabled and a valid 24-hour time.')
        with self._database() as db:
            db.execute('UPDATE schedule SET enabled=?,at=?,pending=CASE WHEN ?=0 THEN NULL ELSE pending END WHERE id=1',
                       (int(enabled),at,int(enabled)))
        return self.get()

    def check(self):
        if not self.path.exists():return self.get()
        with self._database() as db:
            # Serialize generation as well as claiming the date: two checks cannot create two briefings.
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM schedule WHERE id=1').fetchone()
            now=self._now();today=now.date().isoformat()
            if row['enabled'] and now.strftime('%H:%M')>=row['at'] and (not row['last_date'] or row['last_date']<today):
                result=self._briefing.execute('daily briefing')
                if not isinstance(result,dict) or not result.get('ok'):
                    raise RuntimeError('The daily briefing could not be prepared. It will be retried.')
                pending={'date':today,'prepared_at':now.isoformat(timespec='minutes'),'reply':result['reply'],
                         'partial':bool(result.get('partial'))}
                db.execute('UPDATE schedule SET last_date=?,pending=? WHERE id=1',
                           (today,json.dumps(pending,ensure_ascii=False)))
            return self._view(db.execute('SELECT * FROM schedule WHERE id=1').fetchone())

    def dismiss(self,date):
        if not isinstance(date,str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date) or not self.path.exists():
            return False
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM schedule WHERE id=1').fetchone()
            pending=json.loads(row['pending']) if row['pending'] else None
            if not pending or pending['date']!=date:return False
            db.execute('UPDATE schedule SET pending=NULL WHERE id=1')
            return True
