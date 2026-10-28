from datetime import datetime,time,timedelta,timezone
from pathlib import Path
import sys
from unittest.mock import Mock,patch
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from daily_briefing import DailyBriefing
from local_time import local_now,local_timezone

# Both transition days have different UTC offsets at their local day boundaries.
berlin=ZoneInfo('Europe/Berlin')
for date,hours in [(datetime(2026,3,29),23),(datetime(2026,10,25),25)]:
    start=datetime.combine(date.date(),time.min,tzinfo=berlin)
    end=datetime.combine(date.date()+timedelta(days=1),time.min,tzinfo=berlin)
    assert (end.timestamp()-start.timestamp())/3600==hours
    now=start+timedelta(minutes=30)
    weather=Mock();weather.location.return_value={'location':''}
    reminders=Mock()
    next_day=end+timedelta(minutes=15)
    reminders.pending.return_value=[{'id':1,'text':'Correct today item','due':(end-timedelta(minutes=15)).timestamp()},
                                    {'id':2,'text':'Must stay tomorrow','due':next_day.timestamp()}]
    result=DailyBriefing(weather,reminders,now=lambda:now).execute('daily briefing')
    assert 'Correct today item' in result['reply'] and 'Must stay tomorrow' not in result['reply']
# The real runtime clock retains transition-aware rules in this Windows installation.
assert local_now().tzinfo is not None
zone=local_timezone()
if getattr(zone,'_stdname','')=='W. Europe Standard Time':
    assert datetime(2026,7,1,tzinfo=zone).utcoffset()!=datetime(2026,12,1,tzinfo=zone).utcoffset()
print('PASS: 23/25-hour local days, reminder day boundaries and transition-aware runtime timezone')
