from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from briefing_schedule import BriefingSchedule

with tempfile.TemporaryDirectory() as folder:
    now=[datetime(2026,10,28,8,59,tzinfo=timezone(timedelta(hours=1)))]
    briefing=Mock();briefing.execute.return_value={'ok':True,'reply':'A daily snapshot','partial':False}
    path=Path(folder)/'schedule.sqlite3'
    store=BriefingSchedule(briefing,path,now=lambda:now[0])
    assert not store.get()['enabled'] and not store.check()['pending'] and not path.exists()
    for enabled,at in [('yes','09:00'),(True,'24:00'),(True,'09:60'),(True,'9:00')]:
        try:store.configure(enabled,at);raise AssertionError('Invalid setting accepted')
        except ValueError:pass
    store.configure(True,'09:00')
    assert store.check()['pending'] is None
    now[0]+=timedelta(minutes=1)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:BriefingSchedule(briefing,path,now=lambda:now[0]).check(),range(4)))
    assert all(item['pending']['date']=='2026-10-28' for item in results)
    briefing.execute.assert_called_once()
    assert BriefingSchedule(briefing,path,now=lambda:now[0]).get()['pending']['reply']=='A daily snapshot'
    assert not store.dismiss('2026-10-27') and store.dismiss('2026-10-28')
    assert not store.check()['pending']
    store.configure(False,'09:00');store.configure(True,'09:00')
    assert not store.check()['pending'],'Re-enabling must not duplicate the same day'
    now[0]+=timedelta(days=3,hours=2)
    assert store.check()['pending']['date']=='2026-10-31', 'Catch up only for the current date'
    assert briefing.execute.call_count==2
    now[0]-=timedelta(days=1)
    assert store.check()['pending']['date']=='2026-10-31' and briefing.execute.call_count==2
    now[0]+=timedelta(days=2)
    briefing.execute.side_effect=RuntimeError('temporary failure')
    try:store.check();raise AssertionError('Failed generation accepted')
    except RuntimeError:pass
    assert store.get()['last_date']=='2026-10-31'
    briefing.execute.side_effect=None
    briefing.execute.return_value={'ok':True,'reply':'Weather unavailable; reminders listed','partial':True}
    assert store.check()['pending']['partial']
    store.configure(False,'10:00')
    assert not store.get()['enabled'] and store.get()['pending'] is None
print('PASS: opt-in schedule, exact boundary, concurrency, restart persistence, acknowledgement, catch-up, clock rollback and retry')
