"""Persistent one-shot reminders, driven by the desktop's visual reminder inbox."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3
import time
from local_time import local_timezone

DEFAULT_PATH=Path(__file__).resolve().parents[1]/'data'/'reminders.sqlite3'


class Reminders:
    def __init__(self,path=None,clock=time.time):
        self.path=Path(path) if path is not None else DEFAULT_PATH
        self._clock=clock

    @contextmanager
    def _database(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:
            db.execute('''CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL,
                due REAL NOT NULL, state TEXT NOT NULL DEFAULT 'pending')''')
            yield db
            db.commit()
        finally:db.close()

    @staticmethod
    def display_time(timestamp):
        return datetime.fromtimestamp(timestamp,local_timezone()).isoformat(timespec='minutes')

    def create(self,text,due):
        text=' '.join(text.split())
        if not 1<=len(text)<=500:raise ValueError('Use reminder text of 1–500 characters.')
        now=self._clock()
        if not now<due<=now+366*86400:raise ValueError('Choose a future time within the next 366 days.')
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT COUNT(*) FROM reminders WHERE state='pending'").fetchone()[0]>=200:
                raise ValueError('You have 200 active reminders. Cancel or dismiss one first.')
            return db.execute('INSERT INTO reminders(text,due) VALUES (?,?)',(text,due)).lastrowid

    def pending(self):
        if not self.path.exists():return []
        with self._database() as db:
            return [dict(row) for row in db.execute("SELECT id,text,due FROM reminders WHERE state='pending' ORDER BY due,id")]

    def due(self):
        now=self._clock()
        return [{**r,'overdue':now-r['due']>60,'due_local':self.display_time(r['due'])}
                for r in self.pending() if r['due']<=now][:10]

    def finish(self,reminder_id,state):
        if type(reminder_id) is not int or reminder_id<1 or state not in ('dismissed','cancelled'):
            return False
        if not self.path.exists():return False
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            changed=db.execute("UPDATE reminders SET state=? WHERE id=? AND state='pending'",
                               (state,reminder_id)).rowcount
            # Bound terminal history without reusing stable reminder IDs.
            db.execute("DELETE FROM reminders WHERE state!='pending' AND id NOT IN (SELECT id FROM reminders WHERE state!='pending' ORDER BY id DESC LIMIT 200)")
            return bool(changed)

    def execute(self,text):
        if not isinstance(text,str):return {'handled':False}
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',text.strip(),flags=re.I)
        relative=re.fullmatch(r'remind me in ([1-9]\d{0,5}) (minute|hour|day)s? to (.+)',command,re.I|re.S)
        absolute=re.fullmatch(r'remind me at (\S+) to (.+)',command,re.I|re.S)
        listing=re.fullmatch(r'(?:show|list) reminders(?: ([1-9]\d{0,2}))?[.!?]?',command,re.I)
        cancel=re.fullmatch(r'cancel reminder ([1-9]\d{0,8})[.!?]?',command,re.I)
        if not any((relative,absolute,listing,cancel)):
            if re.match(r'^(?:remind me\b|show reminders\b|list reminders\b|cancel reminder\b)',command,re.I):
                return {'handled':True,'ok':False,'reply':'Try “remind me in 10 minutes to stretch”, “show reminders”, or “cancel reminder 1”. For an exact time, include its UTC offset: “remind me at 2026-10-29T09:00+01:00 to call Alex”.'}
            return {'handled':False}
        try:
            if relative or absolute:
                if relative:
                    seconds=int(relative[1])*{'minute':60,'hour':3600,'day':86400}[relative[2].lower()]
                    due=self._clock()+seconds;note=relative[3]
                else:
                    try:date=datetime.fromisoformat(absolute[1])
                    except ValueError:raise ValueError('Use an ISO date/time with a UTC offset, such as 2026-10-29T09:00+01:00.') from None
                    if date.tzinfo is None:raise ValueError('Include the UTC offset in the time, such as +01:00 or +02:00.')
                    due=date.timestamp();note=absolute[2]
                reminder_id=self.create(note,due)
                reply='Reminder '+str(reminder_id)+' set for '+self.display_time(due)+': '+note.strip()+'. Artemis must be open to show it; overdue reminders appear when you reopen it.'
            elif cancel:
                changed=self.finish(int(cancel[1]),'cancelled')
                return {'handled':True,'ok':changed,'reply':'Reminder cancelled.' if changed else 'That reminder is not active.'}
            else:
                page=int(listing[1] or 1);items=self.pending();selected=items[(page-1)*10:page*10]
                reply='\n'.join(str(item['id'])+': '+self.display_time(item['due'])+' — '+item['text'] for item in selected)
                reply=reply or 'No active reminders on this page.'
                if len(items)>10:reply+='\nPage '+str(page)+'. Use “show reminders 2” for page 2.'
            return {'handled':True,'ok':True,'reply':reply}
        except (ValueError,OverflowError) as exc:
            return {'handled':True,'ok':False,'reply':str(exc)}
        except (sqlite3.Error,OSError):
            return {'handled':True,'ok':False,'reply':'Artemis could not access reminders. Your request was not completed.'}
