"""Bounded session-only timing measurements. Never store prompts, text or audio."""
from collections import deque
import math
import threading
import time


class PerformanceLog:
    FIELDS={'first_text_seconds','model_load_seconds','synthesis_seconds',
            'playback_seconds','capture_seconds','transcription_seconds'}

    def __init__(self,limit=50):
        self._records=deque(maxlen=limit)
        self._lock=threading.Lock()

    def record(self,stage,outcome,total_seconds,**measurements):
        if stage not in ('chat','recognition','speech') or outcome not in ('completed','cancelled','error','waiting'):
            return
        def valid(value):
            return type(value) in (int,float) and math.isfinite(value) and value>=0
        if not valid(total_seconds):return
        entry={'stage':stage,'outcome':outcome,'total_seconds':round(total_seconds,3),'finished_at':time.time()}
        entry.update({key:round(value,3) for key,value in measurements.items() if key in self.FIELDS and valid(value)})
        with self._lock:self._records.append(entry)

    def snapshot(self):
        with self._lock:records=[dict(record) for record in self._records]
        summary=[]
        for stage in ('chat','recognition','speech'):
            group=[record for record in records if record['stage']==stage]
            completed=[record for record in group if record['outcome']=='completed']
            summary.append({'stage':stage,'count':len(group),'completed':len(completed),
                'mean_seconds':round(sum(r['total_seconds'] for r in completed)/len(completed),3) if completed else None,
                'latest':group[-1] if group else None})
        return {'retained':len(records),'summary':summary,'recent':list(reversed(records[-10:]))}

    def clear(self):
        with self._lock:self._records.clear()


PERFORMANCE=PerformanceLog()
