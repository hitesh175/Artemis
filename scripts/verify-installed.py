"""Hidden WebView2 integration check against installed files; isolated user state."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

parser=argparse.ArgumentParser()
parser.add_argument('--skip-voice-warmup',action='store_true')
args=parser.parse_args()
ROOT=Path(r'C:\Users\kanag\Desktop\Artemis')
WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'desktop'))
import main
import server
import webview

temporary=tempfile.TemporaryDirectory(dir=WORK/'output')
temp=Path(temporary.name)
def isolated(factory,name):
    return lambda:factory(temp/name)
main.DesktopState=isolated(main.DesktopState,'state.json')
main.PersonalMemory=isolated(main.PersonalMemory,'memory.sqlite3')
main.DocumentSearch=isolated(main.DocumentSearch,'documents.sqlite3')
main.Reminders=isolated(main.Reminders,'reminders.sqlite3')
main.Everyday=isolated(main.Everyday,'weather.json')
main.ModelSettings=isolated(main.ModelSettings,'models.sqlite3')
schedule_factory=main.BriefingSchedule
main.BriefingSchedule=lambda briefing:schedule_factory(briefing,temp/'schedule.sqlite3')
main.CalendarStore=isolated(main.CalendarStore,'calendars.sqlite3')
bridge=main.WindowBridge()
bridge._mini_file=temp/'mini.json'
http=server.make_server(memory=bridge._memory,documents=bridge._documents,model_settings=bridge._models)
threading.Thread(target=http.serve_forever,daemon=True).start()
window=webview.create_window('Artemis installed integration check',url=f'http://127.0.0.1:{http.server_port}',
    js_api=bridge,width=1100,height=800,min_size=(260,260),hidden=True,frameless=True,easy_drag=False)
bridge._window=window
outcome={'passed':False}

def verify():
    try:
        assert window.events.loaded.wait(30),'WebView2 failed to load'
        for _ in range(60):
            if window.evaluate_js('Boolean(window.ArtemisSession?.ready)'):break
            time.sleep(.1)
        assert window.evaluate_js('window.ArtemisSession.ready')
        assert window.evaluate_js('window.ArtemisSession.quiet')
        assert not window.evaluate_js('window.ArtemisHandsfree.enabled')
        if not args.skip_voice_warmup:
            window.evaluate_js("document.getElementById('warm-voice-models').click()")
            for _ in range(900):
                state=bridge.voice_warmup_status()['state']
                if state in ('ready','error'):break
                time.sleep(.1)
            assert bridge.voice_warmup_status()['state']=='ready',bridge.voice_warmup_status()
            assert bridge._voice._thread is None and not bridge._speech.status()['playing']
            assert window.evaluate_js('window.ArtemisSession.quiet')
            outcome['silent_voice_warmup']=bridge.voice_warmup_status()
        else:outcome['silent_voice_warmup']='Skipped for UI-only verification'
        from datetime import datetime
        calendar=temp/'test-calendar.ics'
        calendar.write_text('BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:artemis-check\nDTSTART;VALUE=DATE:'+datetime.now().strftime('%Y%m%d')+'\nSUMMARY:Artemis calendar check\nEND:VEVENT\nEND:VCALENDAR\n',encoding='utf-8')
        bridge._calendar.import_file(calendar)
        assert 'Artemis calendar check' in bridge.handle_command('calendar today')['reply']
        outcome['calendar_import']=True
        for _ in range(30):
            if window.evaluate_js("!document.getElementById('save-briefing-schedule').disabled"):break
            time.sleep(.1)
        assert not bridge.get_briefing_schedule()['enabled']
        window.evaluate_js("document.getElementById('schedule-briefing-enabled').checked=true;document.getElementById('schedule-briefing-time').value='00:00';document.getElementById('save-briefing-schedule').click()")
        for _ in range(60):
            if window.evaluate_js("!document.getElementById('scheduled-briefing-notice').hidden"):break
            time.sleep(.1)
        assert window.evaluate_js("document.getElementById('scheduled-briefing-notice').textContent.includes('Your daily briefing')")
        assert window.evaluate_js("document.getElementById('scheduled-briefing-notice').textContent.includes('Artemis calendar check')")
        window.evaluate_js("document.querySelector('#scheduled-briefing-notice button').click()")
        for _ in range(30):
            if window.evaluate_js("document.getElementById('scheduled-briefing-notice').hidden"):break
            time.sleep(.1)
        assert not bridge.get_briefing_schedule()['pending']
        bridge.set_briefing_schedule(False,'09:00')
        outcome['scheduled_briefing']=True
        assert bridge._voice._thread is None
        assert window.evaluate_js("['index-documents','check-services','stop-reply','reminder-inbox'].every(id=>Boolean(document.getElementById(id)))")
        assert window.evaluate_js("typeof readArtemisStream==='function'")
        window.evaluate_js("void sendArtemisMessage('plan tasks: calculate 2 + 3; what time is it')")
        for _ in range(30):
            if window.evaluate_js("Array.from(document.querySelectorAll('#messages button')).some(button=>button.textContent==='Run these steps')"):break
            time.sleep(.1)
        assert window.evaluate_js("Array.from(document.querySelectorAll('#messages button')).some(button=>button.textContent==='Run these steps')")
        window.evaluate_js("Array.from(document.querySelectorAll('#messages button')).find(button=>button.textContent==='Run these steps').click()")
        for _ in range(30):
            if window.evaluate_js("document.querySelector('#messages .bubble:last-child').textContent.includes('completed.')"):break
            time.sleep(.1)
        assert window.evaluate_js("document.querySelector('#messages .bubble:last-child').textContent.includes('2 + 3 = 5')")
        assert window.evaluate_js("document.querySelector('#messages .bubble:last-child').textContent.includes('completed.')")
        outcome['reviewed_task_plan']=True
        # Exercise the real stop control with synthetic synthesis, without sound.
        from types import SimpleNamespace
        speech_started=threading.Event()
        def synthetic_say(text,cancel_event):
            speech_started.set()
            if not cancel_event.wait(5):raise RuntimeError('Speech cancellation did not arrive')
        bridge._speech.speaker=SimpleNamespace(kokoro=object(),say=synthetic_say)
        bridge._speech.set_enabled(True)
        assert bridge._speech.speak('Silent cancellation test')['ok']
        assert speech_started.wait(2)
        for _ in range(20):
            if window.evaluate_js("!document.getElementById('stop-speaking').hidden"):break
            time.sleep(.1)
        assert window.evaluate_js("!document.getElementById('stop-speaking').hidden")
        window.evaluate_js("document.getElementById('stop-speaking').click()")
        for _ in range(30):
            if not bridge._speech.status()['playing']:break
            time.sleep(.1)
        assert not bridge._speech.status()['playing']
        assert not bridge._speech.status()['error']
        bridge._speech.set_enabled(False)
        outcome['stop_speaking']=True
        window.evaluate_js("document.getElementById('refresh-models').click()")
        for _ in range(60):
            if window.evaluate_js("!document.getElementById('refresh-models').disabled"):break
            time.sleep(.1)
        model_status=window.evaluate_js("document.getElementById('model-status').textContent")
        assert model_status.startswith('Selected: artemis'),model_status
        window.evaluate_js("document.getElementById('save-model').click()")
        for _ in range(60):
            if window.evaluate_js("!document.getElementById('save-model').disabled"):break
            time.sleep(.1)
        assert bridge._models.get()=='artemis'
        assert window.evaluate_js("document.getElementById('model-status').textContent.startsWith('Saved:')")
        outcome['model_selection']=True
        assert window.evaluate_js("Boolean(document.getElementById('daily-briefing'))")
        window.evaluate_js("document.getElementById('daily-briefing').click()")
        for _ in range(60):
            if window.evaluate_js('!busy'):break
            time.sleep(.1)
        assert window.evaluate_js("document.querySelector('#messages .bubble:last-child').textContent.includes('Your daily briefing')")
        outcome['daily_briefing']=True
        # Exercise the actual page, bridge and installed persistence services.
        window.evaluate_js("void sendArtemisMessage('remember that My preferred drink is tea')")
        for _ in range(60):
            if window.evaluate_js('!busy'):break
            time.sleep(.1)
        assert bridge._memory.search('tea')
        assert bridge.handle_command('forget memory 1')['ok']
        document=temp/'sample.txt';document.write_text('Budget approved: 900 euros',encoding='utf-8')
        bridge._documents.index(document)
        assert bridge.handle_command('search documents for budget')['sources'][0]['line_start']==1
        assert bridge.handle_command('remind me in 1 minute to test reminder')['ok']
        with bridge._reminders._database() as db:
            db.execute('UPDATE reminders SET due=?',(time.time()-120,))
        # Let the real page's interval populate the persistent inbox.
        for _ in range(80):
            if window.evaluate_js("!document.getElementById('reminder-inbox').hidden"):break
            time.sleep(.1)
        assert window.evaluate_js("document.getElementById('reminder-inbox').textContent.includes('Overdue reminder')")
        assert bridge.dismiss_reminder(1)['ok']
        # Service check and a short real-model stream through the installed HTTP proxy.
        window.evaluate_js("document.getElementById('check-services').click()")
        for _ in range(60):
            status=window.evaluate_js("document.getElementById('service-status').textContent")
            if not status.startswith('Checking'):break
            time.sleep(.1)
        outcome['services']=status
        if 'Model: ready' in status:
            window.evaluate_js("void sendArtemisMessage('Reply with a short greeting.')")
            for _ in range(1100):
                if window.evaluate_js('!busy'):break
                time.sleep(.1)
            last=window.evaluate_js("document.querySelector('#messages .bubble:last-child').textContent")
            assert last and not last.startswith(('Could not connect:','Thinking')),(last,)
            outcome['live_model_reply']=last
            window.evaluate_js("document.getElementById('refresh-performance').click()")
            for _ in range(30):
                if window.evaluate_js("!document.getElementById('refresh-performance').disabled"):break
                time.sleep(.1)
            assert window.evaluate_js("document.getElementById('performance-results').textContent.includes('Chat request: last')")
            assert bridge.get_performance()['retained']>0
            outcome['performance_panel']=True
        else:
            outcome['live_model_reply']='Not tested: model unavailable'
        for mode in ('mini','chat','full'):
            assert bridge.set_mini_mode(mode)['ok']
        assert bridge._voice._thread is None
        assert not bridge._speech.status()['playing']
        outcome['passed']=True
    except BaseException:
        import traceback
        outcome['error']=traceback.format_exc()
    finally:
        (WORK/'output'/'installed-verification.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
        window.destroy()

try:
    webview.start(verify,gui='edgechromium',debug=False,private_mode=True)
finally:
    http.shutdown();http.server_close();temporary.cleanup()
print(json.dumps(outcome,indent=2))
raise SystemExit(0 if outcome['passed'] else 1)
