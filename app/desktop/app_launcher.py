"""Explicit single-app requests; model replies are never execution instructions."""
import os
import re
import sys
import time
import uuid
import threading
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from artemis.artemis_app_resolver_723 import discover_apps, match_app, launch_shortcut

class AppLauncher:
    def __init__(self):
        self._lock=threading.RLock()
        self._apps=[]
        self._scanned=0.
        self._pending={}

    @staticmethod
    def _parse(text):
        if not isinstance(text,str) or len(text)>3000:return None
        text=re.sub(r'\s+',' ',text).strip()
        text=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',text,flags=re.I)
        match=re.fullmatch(r'(?:(?:can|could|would) you (?:please )?|please )?(?:open|launch|start) (?:the |my )?(.+?)[.!?]?',text,re.I)
        if not match:return None
        target=re.sub(r'\s+(?:please|for me)$','',match.group(1),flags=re.I).strip(' .!?')
        if not target or len(target)>80 or re.search(r'[;&|<>/\\:=`"\r\n]|\b(?:and|then|with|using)\b',target,re.I):return ''
        return target

    def _catalog(self):
        if not self._scanned or time.monotonic()-self._scanned>120:
            self._apps=discover_apps();self._scanned=time.monotonic()
        return self._apps

    def list_apps(self):
        with self._lock:
            try:
                return {'ok':True,'apps':sorted(set(['Notepad','Calculator','File Explorer']+[a.name for a in self._catalog()]))}
            except Exception as exc:return {'ok':False,'error':str(exc)}

    def execute(self,text):
        if isinstance(text,str) and text.casefold().strip(' .?!')=='spotify':
            return {'handled':True,'reply':'To launch Spotify, say “open Spotify”. YouTube and music playback control remain disabled.'}
        if isinstance(text,str) and len(text)<=3000:
            command=re.sub(r'\s+',' ',text).strip()
            command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',command,flags=re.I)
            command=re.sub(r'^(?:(?:can|could|would) you (?:please )?|please )','',command,flags=re.I)
            if (re.match(r'^(?:play|pause|resume|stop|search|find|open|launch|start)\b',command,re.I)
                and re.search(r'\b(?:you\s*tube|music)\b',command,re.I)):
                return {'handled':True,'launched':False,'reply':'YouTube and music control are disabled in Artemis. You can use your YouTube app directly.'}
        if isinstance(text,str) and text.casefold().strip(' .?!') in {
            'can you open apps','can you open programs','what apps can you open',
            'what can you do','help','list commands'}:
            return {'handled':True,'reply':'I can open installed apps when you ask directly. Try “open Notepad”, “open Spotify”, or “launch VS Code”. Find app names in Settings → Open apps → Find apps. Voice commands use the same wording; start hands-free explicitly for automatic turn-taking.'}
        target=self._parse(text)
        if target is None:return {'handled':False}
        if not target:return {'handled':True,'reply':'Please ask me to open one app by name, without extra commands.'}
        with self._lock:
            self._pending.clear()
            try:
                key=target.casefold()
                builtins={'notepad':('Notepad','notepad.exe'),'note pad':('Notepad','notepad.exe'),
                          'calculator':('Calculator','calc.exe'),'file explorer':('File Explorer','explorer.exe'),
                          'explorer':('File Explorer','explorer.exe')}
                if key in builtins:
                    name,exe=builtins[key]
                    program=Path(os.environ.get('WINDIR',r'C:\Windows'))/'System32'/exe
                    if not program.is_file():raise FileNotFoundError(name+' is not available.')
                    subprocess.Popen([str(program)],shell=False)
                    return {'handled':True,'launched':True,'reply':'Opened '+name+'.'}
                aliases={'vs code':'Visual Studio Code','vscode':'Visual Studio Code','edge':'Microsoft Edge','chrome':'Google Chrome'}
                match=match_app(aliases.get(key,target),self._catalog())
                if match.kind=='exact':
                    launch_shortcut(match.app)
                    return {'handled':True,'launched':True,'reply':'Opened '+match.app.name+'.'}
                if match.kind=='confirm' and match.app:
                    token=uuid.uuid4().hex
                    self._pending[token]=(time.monotonic()+60,match.app)
                    return {'handled':True,'reply':'Did you mean '+match.app.name+'? Select Open to confirm.',
                            'confirmation':{'token':token,'name':match.app.name}}
                return {'handled':True,'reply':'I could not find an installed app called '+target+'. Use its Start menu name, or check Find apps in Settings.'}
            except Exception as exc:
                return {'handled':True,'launched':False,'reply':'I could not open '+target+': '+str(exc)}

    def cancel_confirmation(self,token):
        with self._lock:self._pending.pop(token,None)

    def confirm(self,token):
        with self._lock:
            pending=self._pending.pop(token,None) if isinstance(token,str) else None
            if not pending or pending[0]<time.monotonic():
                return {'ok':False,'reply':'That app suggestion expired. Please ask again.'}
            try:
                launch_shortcut(pending[1])
                return {'ok':True,'reply':'Opened '+pending[1].name+'.'}
            except Exception as exc:return {'ok':False,'reply':'Could not open the app: '+str(exc)}
