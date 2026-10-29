"""Silent native UI smoke check of an isolated guided installation, without models."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
args=parser.parse_args()
root=args.root.resolve(strict=True)
work=Path(__file__).resolve().parents[1]/'output'
sys.path[:0]=[str(root/'desktop'),str(root)]
import main
import server
import webview

temporary=tempfile.TemporaryDirectory(dir=work)
temp=Path(temporary.name)
for name,filename in (('DesktopState','state.json'),('PersonalMemory','memory.sqlite3'),
                      ('DocumentSearch','documents.sqlite3'),('Reminders','reminders.sqlite3'),
                      ('Everyday','weather.json'),('ModelSettings','models.sqlite3'),
                      ('CalendarStore','calendar.sqlite3')):
    factory=getattr(main,name)
    setattr(main,name,lambda factory=factory,filename=filename:factory(temp/filename))
factory=main.BriefingSchedule
main.BriefingSchedule=lambda briefing:factory(briefing,temp/'schedule.sqlite3')
bridge=main.WindowBridge()
bridge._mini_file=temp/'mini.json'
http=server.make_server(memory=bridge._memory,documents=bridge._documents,model_settings=bridge._models)
threading.Thread(target=http.serve_forever,daemon=True).start()
window=webview.create_window('Artemis fresh setup check',url=f'http://127.0.0.1:{http.server_port}',
                            js_api=bridge,hidden=True,width=1100,height=800)
bridge._window=window
outcome={'passed':False,'root':str(root),'microphone_used':False,'audio_played':False}

def verify():
    try:
        assert window.events.loaded.wait(30),'Native window did not load'
        for _ in range(100):
            if window.evaluate_js('Boolean(window.ArtemisSession?.ready)'):break
            time.sleep(.1)
        assert window.evaluate_js('window.ArtemisSession.ready')
        assert window.evaluate_js('window.ArtemisSession.quiet')
        assert not window.evaluate_js('window.ArtemisHandsfree.enabled')
        assert not bridge.get_briefing_schedule()['enabled']
        reply=bridge.handle_command('calculate 7 * 8')['reply']
        assert '56' in reply,reply
        assert bridge._voice._thread is None
        assert not bridge._speech.status()['playing']
        assert window.evaluate_js("['check-services','stop-reply','reminder-inbox','warm-voice-models'].every(id=>Boolean(document.getElementById(id)))")
        outcome.update(passed=True,native_webview2=True,quiet_default=True,
                       handsfree_off=True,schedule_off=True,calculation=reply)
    except BaseException:
        import traceback
        outcome['error']=traceback.format_exc()
    finally:window.destroy()

try:webview.start(verify,gui='edgechromium',debug=False,private_mode=True)
finally:
    http.shutdown();http.server_close();temporary.cleanup()
(work/'fresh-install-verification.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
print(json.dumps(outcome,indent=2))
raise SystemExit(0 if outcome['passed'] else 1)
