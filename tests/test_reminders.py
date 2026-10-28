from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from reminders import Reminders

with tempfile.TemporaryDirectory() as folder:
    now=[1800000000.0]
    path=Path(folder)/'reminders.sqlite3'
    store=Reminders(path,clock=lambda:now[0])
    assert store.due()==[] and not path.exists()
    assert not store.execute('explain reminders')['handled']
    assert store.execute('remind me in 10 minutes to stretch')['ok']
    assert store.pending()[0]['due']==now[0]+600
    assert store.due()==[]
    now[0]+=600
    assert store.due()[0]['text']=='stretch' and not store.due()[0]['overdue']
    assert store.due()[0]['id']==1, 'Polling must not consume the reminder'
    now[0]+=120
    reopened=Reminders(path,clock=lambda:now[0])
    assert reopened.due()[0]['overdue']
    assert reopened.finish(1,'dismissed') and not reopened.due()
    assert not reopened.finish(1,'dismissed')
    assert not reopened.finish('1','cancelled')
    assert store.execute('remind me at 2030-01-01T09:00 to call Alex')['ok'] is False
    assert store.execute('remind me in 0 minutes to stretch')['ok'] is False
    assert store.execute('remind me in 999999 days to stretch')['ok'] is False
    assert store.execute('remind me in 1 minute to '+('x'*501))['ok'] is False
    assert store.execute('cancel reminder all')['ok'] is False
    due=now[0]+3600
    from datetime import datetime,timezone
    date=datetime.fromtimestamp(due,timezone.utc).isoformat()
    assert store.execute('remind me at '+date+' to check budget')['ok']
    assert store.pending()[0]['due']==due
    assert store.execute('cancel reminder 2')['ok']
    assert not store.pending()
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids=list(pool.map(lambda n:Reminders(path,clock=lambda:now[0]).create('Item '+str(n),now[0]+60),range(12)))
    assert len(set(ids))==12
    assert 'Page 1' in store.execute('show reminders')['reply']
    assert 'Page 2' in store.execute('show reminders 2')['reply']
    now[0]+=61
    assert len(store.due())==10
    assert store.finish(store.due()[0]['id'],'dismissed')
    assert len(store.due())==10, 'Inbox must advance to remaining overdue reminders'
    broken=Reminders(Path(folder)/'broken.sqlite3')
    broken.path.write_bytes(b'not a database')
    assert not broken.execute('show reminders')['ok']
print('PASS: reminder scheduling, restart catch-up, repeated polling, acknowledgement, cancellation, offsets, limits and concurrency')
