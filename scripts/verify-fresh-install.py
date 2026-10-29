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
parser.add_argument('--visible',action='store_true',help='Show the test window to verify real animation frames')
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
                            js_api=bridge,hidden=not args.visible,width=1100,height=800)
bridge._window=window
outcome={'passed':False,'root':str(root),'microphone_used':False,'audio_played':False}

def verify():
    try:
        assert window.events.loaded.wait(30),'Native window did not load'
        for _ in range(100):
            if window.evaluate_js('Boolean(window.ArtemisSession?.ready)'):break
            time.sleep(.1)
        assert window.evaluate_js('window.ArtemisSession.ready')
        window.evaluate_js("openPanel('settings')")
        assert window.evaluate_js("getComputedStyle(document.getElementById('settings-panel')).visibility==='visible'")
        assert window.evaluate_js("document.getElementById('chat-panel').inert")
        assert window.evaluate_js("getComputedStyle(document.querySelector('.icon-energy path')).animationPlayState==='paused'")
        window.evaluate_js("closePanels()")
        assert window.evaluate_js("getComputedStyle(document.getElementById('settings-panel')).contentVisibility==='hidden'")
        window.evaluate_js("openPanel('chat')")
        if args.visible:
            window.evaluate_js("window.renderCheck={writes:0}; const probe=document.createElement('div'); document.getElementById('messages').appendChild(probe); const observe=new MutationObserver(records=>window.renderCheck.writes+=records.length); observe.observe(probe,{childList:true}); const renderer=createArtemisReplyRenderer(probe,document.getElementById('messages')); for(let i=1;i<=500;i++)renderer.update('x'.repeat(i)); requestAnimationFrame(()=>{renderer.finish();window.renderCheck.text=probe.textContent.length;window.renderCheck.done=true;observe.disconnect();probe.remove();});")
            for _ in range(100):
                if window.evaluate_js('Boolean(window.renderCheck.done)'):break
                time.sleep(.1)
            assert window.evaluate_js('window.renderCheck.text===500 && window.renderCheck.writes<=1'),window.evaluate_js('window.renderCheck')
            outcome['native_batched_stream']=True
        outcome['panels_verified']=True
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
