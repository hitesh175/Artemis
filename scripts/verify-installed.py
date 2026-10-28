"""Hidden WebView2 integration check against installed files; isolated user state."""
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

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
bridge=main.WindowBridge()
bridge._mini_file=temp/'mini.json'
http=server.make_server(memory=bridge._memory,documents=bridge._documents)
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
        assert bridge._voice._thread is None
        assert window.evaluate_js("['index-documents','check-services','stop-reply','reminder-inbox'].every(id=>Boolean(document.getElementById(id)))")
        assert window.evaluate_js("typeof readArtemisStream==='function'")
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
