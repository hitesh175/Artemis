"""Reviewed, bounded deterministic task plans. App launching is allowed only last."""
import re
import threading
import time
import uuid
from app_launcher import AppLauncher


class TaskPlans:
    TERMINAL={'completed','failed','cancelled','expired'}

    def __init__(self,router,apps,clock=time.monotonic):
        self._router=router;self._apps=apps;self._clock=clock
        self._lock=threading.RLock();self._plans={}

    @staticmethod
    def _kind(step):
        lower=step.casefold()
        if lower in ('weather today','weather tomorrow','what time is it','what is the date',
                     'daily briefing','calendar today','show reminders','show memories'):
            return 'read'
        if re.fullmatch(r'calculate\s+[-+.(\d][\d\s.+*/%()^×÷-]*',lower):return 'read'
        if re.fullmatch(r'(?:search documents for|find memories about)\s+.+',step,re.I):return 'read'
        if re.match(r'^(?:open|launch|start) ',step,re.I) and AppLauncher._parse(step):return 'app'
        return None

    def _invalidate(self,plan):
        if plan.get('app_token'):
            self._apps.cancel_confirmation(plan.pop('app_token'))

    def _get(self,token):
        plan=self._plans.get(token) if isinstance(token,str) else None
        if plan and plan['expires']<self._clock() and plan['phase'] not in self.TERMINAL and plan['phase']!='running':
            self._invalidate(plan);plan['phase']='expired'
        return plan

    def _view(self,plan):
        plan['revision']=plan.get('revision',0)+1
        lines=['Task plan '+plan['token'][:8]+' — '+plan['phase']+'.']
        for index,step in enumerate(plan['steps']):
            lines.append(str(index+1)+'. '+step)
            if index<len(plan['results']):lines.append(plan['results'][index])
            elif plan['phase'] in self.TERMINAL:lines.append('Not run.')
        if plan['phase']=='preview':lines.append('Review these steps, then click Run these steps. No step has run yet.')
        if plan['phase']=='running' and plan.get('cancel'):lines.append('Stopping after the current step. Already completed actions are not undone.')
        if plan['phase']=='cancelled':lines.append('Stopped. Already completed actions were not undone.')
        if plan['phase']=='failed':lines.append('Stopped at the failed step. Later steps did not run.')
        if plan['phase']=='expired':lines.append('This plan expired. Create a new plan to run it.')
        metadata={'token':plan['token'],'phase':plan['phase'],'cancelling':bool(plan.get('cancel')),'revision':plan['revision']}
        if plan['phase']=='needs_confirmation':metadata['app_name']=plan['app_name']
        return {'handled':True,'ok':plan['phase'] not in ('failed','expired'),'reply':'\n\n'.join(lines)[:11000],
                'task_plan':metadata,'spoken_reply':'Review the task plan in chat.'}

    @staticmethod
    def _missing():return {'ok':False,'reply':'That task plan is no longer available. Create a new plan.'}

    def plan(self,text):
        if not isinstance(text,str):return {'handled':False}
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',text.strip(),flags=re.I)
        if not re.match(r'^(?:plan|run) tasks\b',command,re.I):return {'handled':False}
        match=re.fullmatch(r'(?:plan|run) tasks:\s*(.+)',command,re.I|re.S)
        steps=[part.strip() for part in match[1].split(';')] if match else []
        kinds=[self._kind(step) for step in steps]
        if len(text)>3000 or not 2<=len(steps)<=4 or any(not step or len(step)>500 for step in steps) or None in kinds or 'app' in kinds[:-1]:
            return {'handled':True,'ok':False,'reply':'Use 2–4 supported steps separated by semicolons, with an app launch only as the last step. Example: plan tasks: what time is it; calculate 25 * 4; open Notepad. Supported reads: weather today/tomorrow, daily briefing, calendar today, show reminders/memories, search documents for a topic, and find memories about a topic.'}
        with self._lock:
            for key in list(self._plans):
                old=self._get(key)
                if old['phase'] in self.TERMINAL:del self._plans[key]
            if len(self._plans)>=10:return {'handled':True,'ok':False,'reply':'Finish or cancel an existing plan before creating another.'}
            token=uuid.uuid4().hex
            plan={'token':token,'expires':self._clock()+300,'phase':'preview','steps':steps,'kinds':kinds,'results':[]}
            self._plans[token]=plan
            return self._view(plan)

    def run(self,token):
        with self._lock:
            plan=self._get(token)
            if not plan:return self._missing()
            if plan['phase']!='preview':return self._view(plan)
            plan['phase']='running'
        for index,step in enumerate(plan['steps']):
            with self._lock:
                if plan.get('cancel'):
                    plan['phase']='cancelled';return self._view(plan)
            try:
                if plan['kinds'][index]=='app':
                    # Serialize final launch with cancellation. An already started launch is not undone.
                    with self._lock:
                        if plan.get('cancel'):
                            plan['phase']='cancelled';return self._view(plan)
                        result=self._apps.execute(step)
                else:result=self._router.execute(step)
            except Exception:result={'handled':True,'ok':False,'reply':'This step could not be completed.'}
            if not isinstance(result,dict):result={'handled':True,'ok':False,'reply':'This step returned an invalid result.'}
            with self._lock:
                plan['results'].append(str(result.get('reply','No result returned.'))[:2000])
                if plan.get('cancel'):
                    if result.get('confirmation'):self._apps.cancel_confirmation(result['confirmation']['token'])
                    plan['phase']='cancelled';return self._view(plan)
                if plan['kinds'][index]=='app' and result.get('confirmation'):
                    plan.update(phase='needs_confirmation',app_token=result['confirmation']['token'],app_name=result['confirmation']['name'])
                    return self._view(plan)
                success=result.get('launched') is True if plan['kinds'][index]=='app' else result.get('ok') is True and not result.get('partial')
                if not result.get('handled') or not success:
                    plan['phase']='failed';return self._view(plan)
        with self._lock:
            plan['phase']='completed';return self._view(plan)

    def confirm_app(self,token):
        with self._lock:
            plan=self._get(token)
            if not plan:return self._missing()
            if plan['phase']!='needs_confirmation':return self._view(plan)
            app_token=plan.pop('app_token')
            try:result=self._apps.confirm(app_token)
            except Exception:result={'ok':False,'reply':'The app could not be opened.'}
            plan['results'][-1]=str(result.get('reply','No app result.'))[:2000]
            plan['phase']='completed' if result.get('ok') else 'failed'
            return self._view(plan)

    def cancel(self,token):
        with self._lock:
            plan=self._get(token)
            if not plan:return self._missing()
            if plan['phase'] in self.TERMINAL:return self._view(plan)
            self._invalidate(plan);plan['cancel']=True
            if plan['phase']!='running':plan['phase']='cancelled'
            return self._view(plan)
