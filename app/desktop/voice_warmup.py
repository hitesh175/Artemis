"""Explicit silent speech-model preparation. No recording, playback or downloads."""
import threading
import time


class VoiceWarmup:
    def __init__(self,recognizer,speech):
        self._recognizer=recognizer;self._speech=speech
        self._lock=threading.Lock()
        self._status={'state':'idle','stage':'','results':[],'seconds':0}

    def status(self):
        with self._lock:
            return {**self._status,'results':[dict(result) for result in self._status['results']]}

    def busy(self):
        return self.status()['state']=='loading'

    def start(self):
        with self._lock:
            if self._status['state']=='loading':return {'ok':False,'error':'Voice models are already warming up.'}
            self._status={'state':'loading','stage':'Starting','results':[],'seconds':0}
        threading.Thread(target=self._run,daemon=True).start()
        return {'ok':True}

    def _run(self):
        started=time.perf_counter();results=[]
        for name,prepare in [('Speech recognition',self._recognizer.prepare),
                             ('Speech generation',lambda:self._speech.prepare().prime())]:
            with self._lock:self._status['stage']=name
            step=time.perf_counter()
            try:
                engine=prepare()
                result={'component':name,'ready':True,'model':engine,'seconds':round(time.perf_counter()-step,2)}
            except Exception as exc:
                result={'component':name,'ready':False,'error':str(exc),'seconds':round(time.perf_counter()-step,2)}
            results.append(result)
            with self._lock:self._status['results']=results.copy()
        with self._lock:
            self._status.update(state='ready' if all(r['ready'] for r in results) else 'error',
                                stage='',seconds=round(time.perf_counter()-started,2))
