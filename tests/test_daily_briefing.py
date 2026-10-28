from datetime import datetime,timezone,timedelta
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from daily_briefing import DailyBriefing
from reminders import Reminders

now=datetime(2026,10,28,9,tzinfo=timezone(timedelta(hours=1)))
with tempfile.TemporaryDirectory() as folder:
    reminders=Reminders(Path(folder)/'reminders.sqlite3',clock=lambda:now.timestamp()-3600)
    reminders.create('Already due',now.timestamp()-60)
    reminders.create('Today task',now.timestamp()+3600)
    reminders.create('Tomorrow task',now.timestamp()+86400)
    everyday=Mock()
    everyday.location.return_value={'location':'Berlin'}
    everyday.execute.return_value={'reply':'Berlin today. Currently 12°C. Data time: 2026-10-28 09:00. Source: Open-Meteo.'}
    briefing=DailyBriefing(everyday,reminders,now=lambda:now)
    result=briefing.execute('please give me my daily briefing')
    assert result['ok'] and not result['partial']
    assert 'Already due' in result['reply'] and 'Today task' in result['reply']
    assert 'Tomorrow task' not in result['reply']
    assert '28 October 2026' in result['reply']
    assert 'Data time:' not in result['spoken_reply'] and '12°C' in result['spoken_reply']
    assert result['sources'][0]['name']=='Open-Meteo'
    assert len(reminders.pending())==3,'Briefing must not consume reminders'
    assert not briefing.execute('explain how briefings work')['handled']
    everyday.location.return_value={'location':''};everyday.execute.reset_mock()
    assert 'Set your weather city' in briefing.execute('daily briefing')['reply']
    everyday.execute.assert_not_called()
    everyday.location.return_value={'location':'Berlin'}
    everyday.execute.return_value={'reply':'I could not retrieve live weather.'}
    assert briefing.execute('daily briefing')['partial']
    everyday.execute.side_effect=RuntimeError('weather down')
    with_reminders=briefing.execute('daily briefing')
    assert 'Today task' in with_reminders['reply'] and with_reminders['partial']
    broken=Mock();broken.pending.side_effect=OSError('database down')
    assert 'does not mean you have none' in DailyBriefing(everyday,broken,now=lambda:now).execute('daily briefing')['reply']
    # Local midnight boundary, not UTC midnight.
    late=datetime(2026,10,28,23,30,tzinfo=timezone(timedelta(hours=1)))
    boundary=Mock();boundary.pending.return_value=[{'id':1,'text':'Next local day','due':late.timestamp()+3600}]
    assert 'Next local day' not in DailyBriefing(everyday,boundary,now=lambda:late).execute('daily briefing')['reply']
    long_reminders=Mock()
    long_reminders.pending.return_value=[{'id':index+1,'due':now.timestamp()+(-60 if index<5 else 60),'text':'Long reminder '*35} for index in range(10)]
    long_calendar=Mock();long_calendar.calendars.return_value=[{}]
    long_calendar.today.return_value=[{'time':'All day','summary':'Long title '*27,'location':'Long place '*18,'calendar_id':1} for _ in range(5)]
    long_briefing=DailyBriefing(everyday,long_reminders,now=lambda:now,calendar=long_calendar).execute('daily briefing')
    assert len(long_briefing['reply'])>5000 and len(long_briefing['spoken_reply'])<=5000
    assert 'More details are shown in chat' in long_briefing['spoken_reply']
print('PASS: sourced weather, today/overdue reminders, local date boundaries, partial failures and no reminder consumption')
