from datetime import datetime
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from calendar_store import CalendarStore
from daily_briefing import DailyBriefing

def calendar(*events):
    return ('BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Artemis tests//EN\r\n'+''.join(events)+'END:VCALENDAR\r\n').encode()
def event(uid,start,summary,extra=''):
    return 'BEGIN:VEVENT\r\nUID:'+uid+'\r\nDTSTART'+start+'\r\nSUMMARY:'+summary+'\r\n'+extra+'END:VEVENT\r\n'

now=datetime(2026,10,28,9,tzinfo=ZoneInfo('Europe/Berlin'))
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);store=CalendarStore(root/'calendars.sqlite3');path=root/'school.ics'
    assert store.today(now)==[] and not store.path.exists()
    path.write_bytes(calendar(
        event('all',';VALUE=DATE:20261028','Holiday'),
        event('utc',':20261028T110000Z','Class in UTC'),
        event('floating',':20261028T150000','Floating meeting'),
        event('daily',';TZID=Europe/Berlin:20261026T080000','Daily class','RRULE:FREQ=DAILY;COUNT=5\r\nEXDATE;TZID=Europe/Berlin:20261027T080000\r\n'),
        event('cancel',':20261028T100000Z','Cancelled class','STATUS:CANCELLED\r\n'),
        event('tomorrow',':20261029T120000Z','Tomorrow meeting')))
    calendar_id=store.import_file(path);assert calendar_id==1
    rows=store.today(now)
    assert [row['summary'] for row in rows]==['Holiday','Daily class','Class in UTC','Floating meeting'],rows
    assert rows[0]['time']=='All day' and rows[2]['time'].startswith('12:00')
    assert 'Daily class' not in str(store.today(now.replace(day=27)))
    assert CalendarStore(store.path).today(now)==rows
    assert 'school.ics' in store.execute('list calendars')['reply']
    assert not store.execute('remove calendar all')['ok']
    everyday=Mock();everyday.location.return_value={'location':''}
    reminders=Mock();reminders.pending.return_value=[]
    briefing=DailyBriefing(everyday,reminders,now=lambda:now,calendar=store)
    assert 'Daily class' in briefing.execute('daily briefing')['reply']
    assert '[Calendar 1]' in briefing.execute('daily briefing')['reply']
    # A named recurring time keeps wall-clock time over DST.
    path.write_bytes(calendar(event('dst',';TZID=Europe/Berlin:20261023T090000','DST meeting','RRULE:FREQ=DAILY;COUNT=7\r\n')))
    assert store.import_file(path)==calendar_id
    assert store.today(now.replace(day=24))[0]['time'].startswith('09:00')
    assert store.today(now.replace(day=26))[0]['time'].startswith('09:00')
    path.write_bytes(calendar(event('fast',':20261028T080000Z','Too frequent','RRULE:FREQ=SECONDLY\r\n')))
    try:store.import_file(path);raise AssertionError('Unsupported recurrence accepted')
    except ValueError:pass
    assert store.today(now)[0]['summary']=='DST meeting','Failed refresh must retain snapshot'
    path.write_bytes(b'not an ics file')
    try:store.import_file(path);raise AssertionError('Broken file accepted')
    except ValueError:pass
    assert store.execute('remove calendar 1')['ok'] and path.exists()
    assert store.today(now)==[]
    broken=Mock();broken.calendars.return_value=[{}];broken.today.side_effect=OSError('broken')
    assert DailyBriefing(everyday,reminders,now=lambda:now,calendar=broken).execute('daily briefing')['partial']
print('PASS: selected calendar snapshots, all-day/UTC/floating events, recurring exceptions, DST, cancellations, refresh and briefing integration')
