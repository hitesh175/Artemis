"""Explicit local iCalendar snapshots. Never fetch links or modify a calendar."""
from contextlib import contextmanager
from datetime import datetime,time,timedelta
import json
from pathlib import Path
import re
import sqlite3
from local_time import local_now

DEFAULT_PATH=Path(__file__).resolve().parents[1]/'data'/'calendars.sqlite3'


class CalendarStore:
    def __init__(self,path=None):
        self.path=Path(path) if path is not None else DEFAULT_PATH

    @contextmanager
    def _database(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        db=sqlite3.connect(self.path,timeout=5);db.row_factory=sqlite3.Row
        try:
            db.execute('CREATE TABLE IF NOT EXISTS calendars(id INTEGER PRIMARY KEY AUTOINCREMENT,path TEXT UNIQUE,data BLOB,imported_at TEXT)')
            yield db;db.commit()
        finally:db.close()

    @staticmethod
    def _parse(data):
        from icalendar import Calendar
        try:
            calendar=Calendar.from_ical(data)
            events=calendar.walk('VEVENT')
            if not events or len(events)>500:raise ValueError('Choose a calendar with 1–500 events.')
            if str(calendar.get('METHOD','')).upper()=='CANCEL':raise ValueError('Choose a complete calendar export rather than a cancellation message.')
            for event in events:
                if not event.get('DTSTART') or not event.get('UID'):raise ValueError('Each event needs a start date and UID.')
                for key in ('DTSTART','DTEND','RECURRENCE-ID'):
                    value=event.get(key)
                    if value and isinstance(value.dt,datetime) and value.params.get('TZID') and value.dt.tzinfo is None:
                        raise ValueError('An event has an unknown timezone. Export the calendar with standard timezone names.')
                rule=event.get('RRULE')
                if rule:
                    if str(rule.get('FREQ',[''])[0]) not in ('DAILY','WEEKLY','MONTHLY','YEARLY'):
                        raise ValueError('Only daily, weekly, monthly and yearly repeating events are supported.')
                    if any(len(rule.get(key,[]))>1 for key in ('BYHOUR','BYMINUTE','BYSECOND')):
                        raise ValueError('High-frequency recurrence rules are not supported.')
            return calendar
        except ValueError:raise
        except Exception:raise ValueError('The calendar file could not be read. Choose a valid .ics export.') from None

    def import_file(self,filename):
        path=Path(filename).resolve(strict=True)
        if path.suffix.casefold()!='.ics' or not path.is_file():raise ValueError('Choose an .ics calendar file.')
        with path.open('rb') as source:data=source.read(1000001)
        if len(data)>1000000:raise ValueError('Choose a calendar no larger than 1 MB.')
        self._parse(data)
        with self._database() as db:
            db.execute('BEGIN IMMEDIATE')
            old=db.execute('SELECT id FROM calendars WHERE path=?',(str(path),)).fetchone()
            if not old and db.execute('SELECT COUNT(*) FROM calendars').fetchone()[0]>=5:
                raise ValueError('Remove a calendar before importing more than five.')
            at=datetime.now().astimezone().isoformat(timespec='minutes')
            if old:
                db.execute('UPDATE calendars SET data=?,imported_at=? WHERE id=?',(data,at,old['id']))
                return old['id']
            return db.execute('INSERT INTO calendars(path,data,imported_at) VALUES (?,?,?)',(str(path),data,at)).lastrowid

    def calendars(self):
        if not self.path.exists():return []
        with self._database() as db:return [dict(row) for row in db.execute('SELECT id,path,imported_at FROM calendars ORDER BY id')]

    def remove(self,calendar_id):
        if not self.path.exists():return False
        with self._database() as db:return bool(db.execute('DELETE FROM calendars WHERE id=?',(calendar_id,)).rowcount)

    def today(self,now):
        if not self.path.exists():return []
        import recurring_ical_events
        start=datetime.combine(now.date(),time.min,tzinfo=now.tzinfo)
        end=datetime.combine(now.date()+timedelta(days=1),time.min,tzinfo=now.tzinfo)
        with self._database() as db:rows=[dict(row) for row in db.execute('SELECT * FROM calendars ORDER BY id')]
        output=[]
        for row in rows:
            calendar=self._parse(row['data'])
            for event in calendar.walk('VEVENT'):
                # Floating event times belong to the computer's local timezone.
                for key in ('DTSTART','DTEND','RECURRENCE-ID'):
                    value=event.get(key)
                    if value and isinstance(value.dt,datetime) and value.dt.tzinfo is None:value.dt=value.dt.replace(tzinfo=now.tzinfo)
            for event in recurring_ical_events.of(calendar).between(start,end):
                if str(event.get('STATUS','')).upper()=='CANCELLED':continue
                date=event['DTSTART'].dt
                all_day=not isinstance(date,datetime)
                local=date.astimezone(now.tzinfo) if not all_day else date
                output.append({'calendar_id':row['id'],'calendar':Path(row['path']).name,'imported_at':row['imported_at'],
                    'summary':str(event.get('SUMMARY','Untitled event'))[:300],
                    'location':str(event.get('LOCATION',''))[:200],
                    'time':'All day' if all_day else local.strftime('%H:%M %Z'),
                    'sort':start.timestamp()-1 if all_day else local.timestamp()})
                if len(output)>500:raise ValueError('More than 500 events overlap today. Import a smaller calendar.')
        return sorted(output,key=lambda event:(event['sort'],event['summary']))

    def execute(self,text):
        if not isinstance(text,str):return {'handled':False}
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',text.strip(),flags=re.I).strip(' .?!')
        remove=re.fullmatch(r'remove calendar ([1-9]\d{0,8})',command,re.I)
        if command.casefold() not in ('calendar today','my calendar today','list calendars') and not remove:
            if re.match(r'^(?:calendar today|list calendars|remove calendar)\b',command,re.I):
                return {'handled':True,'ok':False,'reply':'Try “calendar today”, “list calendars”, or “remove calendar 1”.'}
            return {'handled':False}
        try:
            if remove:
                changed=self.remove(int(remove[1]))
                return {'handled':True,'ok':changed,'reply':'Calendar snapshot removed. The original file was kept.' if changed else 'That calendar is not imported.'}
            if command.casefold()=='list calendars':
                reply='\n'.join(str(row['id'])+': '+row['path']+' · imported '+row['imported_at'] for row in self.calendars())
            else:
                rows=self.today(local_now())
                reply='\n'.join(event['time']+' — '+event['summary']+(' · '+event['location'] if event['location'] else '')+
                    ' [Calendar '+str(event['calendar_id'])+']' for event in rows[:15])
                if len(rows)>15:reply+='\nShowing the first 15 of '+str(len(rows))+' events.'
            return {'handled':True,'ok':True,'reply':reply or 'No matching events or imported calendars. Import an .ics file in Settings → Calendar.'}
        except Exception:return {'handled':True,'ok':False,'reply':'The imported calendar could not be read. Refresh its .ics snapshot in Settings.'}
