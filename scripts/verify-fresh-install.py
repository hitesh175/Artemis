"""Silent native UI smoke check of an isolated guided installation, without models."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import time

parser=argparse.ArgumentParser()
parser.add_argument('--root',type=Path,required=True)
parser.add_argument('--visible',action='store_true',help='Show the test window to verify real animation frames')
parser.add_argument('--review-settings',action='store_true',help='Keep an isolated Settings preview open for visual review')
parser.add_argument('--review-width',type=int,default=1100,help='Window width for the isolated Settings preview')
parser.add_argument('--review-section',choices=('appearance','briefings','models','chat'),default='appearance',
                    help='Section or sample conversation to show in the isolated preview')
parser.add_argument('--export-settings',type=Path,help='Export lossless, double-density Settings screenshots from WebView2')
parser.add_argument('--export-overview',type=Path,help='Export fresh home/chat PNGs with an actual sample conversation')
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
                            js_api=bridge,hidden=not (args.visible or args.review_settings or args.export_settings or args.export_overview),
                            width=max(500,min(args.review_width,1600)) if args.review_settings else 1100,height=800,
                            frameless=True,easy_drag=False)
bridge._window=window
outcome={'passed':False,'root':str(root),'microphone_used':False,'audio_played':False}

def prepare_export(css_width=520,css_height=800):
    """Render at double density rather than enlarging an existing image."""
    from System import Action
    from System.Drawing import Size
    from System.Windows.Forms import DockStyle
    native=window.native
    control=native.webview
    original_density=window.evaluate_js('devicePixelRatio')
    def configure():
        native.ClientSize=Size(css_width*2,css_height*2)
        control.Dock=getattr(DockStyle,'None')
        control.Size=Size(css_width*2,css_height*2)
        control.ZoomFactor=control.ZoomFactor*2.0/original_density
    control.Invoke(Action(configure))
    for _ in range(60):
        metrics=window.evaluate_js('({width:innerWidth,height:innerHeight,density:devicePixelRatio})')
        if abs(metrics['width']-css_width)<=2 and abs(metrics['height']-css_height)<=2:break
        time.sleep(.1)
    assert abs(metrics['width']-css_width)<=2 and abs(metrics['height']-css_height)<=2,metrics
    return metrics

def capture_png(path,minimum_width=1040,minimum_height=1500):
    from System import Action
    from System.IO import FileStream,FileMode,FileAccess
    from Microsoft.Web.WebView2.Core import CoreWebView2CapturePreviewImageFormat
    control=window.native.webview
    path.parent.mkdir(parents=True,exist_ok=True)
    time.sleep(.35)
    stream=FileStream(str(path),FileMode.Create,FileAccess.Write)
    tasks=[]
    try:
        control.Invoke(Action(lambda:tasks.append(control.CoreWebView2.CapturePreviewAsync(
            CoreWebView2CapturePreviewImageFormat.Png,stream))))
        if not tasks[0].Wait(15000):raise TimeoutError('WebView2 screenshot timed out')
    finally:stream.Dispose()
    data=path.read_bytes()
    assert data[:8]==b'\x89PNG\r\n\x1a\n','Capture is not a PNG'
    width=int.from_bytes(data[16:20],'big');height=int.from_bytes(data[20:24],'big')
    assert width>=minimum_width and height>=minimum_height,(width,height)
    return {'file':str(path),'width':width,'height':height,'sha256':hashlib.sha256(data).hexdigest()}

def export_settings(destination):
    destination=destination.resolve()
    metrics=prepare_export()
    layout=window.evaluate_js("(()=>{openPanel('settings');const panel=document.getElementById('settings-panel');panel.style.cssText+=';transition:none!important;transform:none!important';return {classes:panel.className,style:panel.style.cssText,transform:getComputedStyle(panel).transform,x:panel.getBoundingClientRect().x}})()")
    assert layout['x']<100,layout
    captures=[]
    digests=set()
    for name,heading in (('artemis-settings','setting-quiet-mode'),
                         ('artemis-settings-workflows','setting-scheduled-daily-briefing'),
                         ('artemis-settings-models','setting-service-status')):
        window.evaluate_js('document.getElementById('+json.dumps(heading)+
                           ").closest('section').scrollIntoView({block:'start',behavior:'instant'});")
        path=destination/(name+'.png')
        capture=capture_png(path)
        digest=capture['sha256']
        assert digest not in digests,'Settings sections produced identical images'
        digests.add(digest)
        captures.append(capture)
    return {'viewport':metrics,'captures':captures}

def export_overview(destination):
    destination=destination.resolve()
    home_metrics=prepare_export(1100,800)
    window.evaluate_js("(()=>{closePanels();return document.getElementById('headline').textContent;})()")
    home=capture_png(destination/'artemis-desktop.png',2200,1600)
    chat_metrics=prepare_export()
    window.evaluate_js("(()=>{openPanel('chat');const panel=document.getElementById('chat-panel');panel.style.cssText+=';transition:none!important;transform:none!important';void(async()=>{await sendArtemisMessage('Give me one practical study tip in a single short sentence.');await sendArtemisMessage('calculate 25 * 4');window.docsChatReady=true;})();})()")
    for _ in range(1200):
        if window.evaluate_js('Boolean(window.docsChatReady)'):break
        time.sleep(.1)
    assert window.evaluate_js('Boolean(window.docsChatReady)'),'Sample conversation did not finish'
    messages=window.evaluate_js("Array.from(document.querySelectorAll('#messages .bubble')).map(node=>node.textContent)")
    assert len(messages)==4,messages
    assert messages[1] and not messages[1].startswith(('Could not connect:','Thinking')) and len(messages[1])<500,messages
    assert '100' in messages[-1],messages
    window.evaluate_js("(()=>{const messages=document.getElementById('messages');messages.scrollTop=messages.scrollHeight;return messages.scrollTop;})()")
    chat=capture_png(destination/'artemis-chat.png')
    return {'home_viewport':home_metrics,'chat_viewport':chat_metrics,'captures':[home,chat],'sample_messages':messages}

def verify():
    try:
        assert window.events.loaded.wait(30),'Native window did not load'
        for _ in range(100):
            if window.evaluate_js('Boolean(window.ArtemisSession?.ready)'):break
            time.sleep(.1)
        assert window.evaluate_js('window.ArtemisSession.ready')
        if args.export_overview:
            outcome.update(overview_export=export_overview(args.export_overview),passed=True)
            return
        if args.export_settings:
            outcome.update(settings_export=export_settings(args.export_settings),passed=True)
            return
        if args.review_settings:
            if args.review_section=='chat':
                window.evaluate_js("openPanel('chat'); void (async()=>{await sendArtemisMessage('Give me one practical study tip in a single short sentence.');await sendArtemisMessage('calculate 25 * 4');})();")
            else:
                heading={'appearance':'setting-quiet-mode','briefings':'setting-scheduled-daily-briefing',
                         'models':'setting-local-intelligence'}[args.review_section]
                window.evaluate_js("openPanel('settings'); document.getElementById("+json.dumps(heading)+
                                   ").closest('section').scrollIntoView({block:'start',behavior:'instant'});")
            outcome['passed']=True
            return
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
    finally:
        if args.export_settings or args.export_overview or not args.review_settings:window.destroy()

try:webview.start(verify,gui='edgechromium',debug=False,private_mode=True)
finally:
    http.shutdown();http.server_close();temporary.cleanup()
(work/'fresh-install-verification.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
print(json.dumps(outcome,indent=2))
raise SystemExit(0 if outcome['passed'] else 1)
