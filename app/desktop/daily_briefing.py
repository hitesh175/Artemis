"""On-demand daily briefing from real weather and saved reminders; no LLM needed."""
from datetime import datetime, timezone
import re
from local_time import local_now


class DailyBriefing:
    def __init__(self,everyday,reminders,now=None,calendar=None):
        self._everyday=everyday
        self._reminders=reminders
        self._calendar=calendar
        self._now=now or local_now

    def execute(self,text):
        if not isinstance(text,str):return {'handled':False}
        command=re.sub(r'\s+',' ',text.strip()).casefold().strip(' .?!')
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',command)
        command=re.sub(r'^(?:(?:can|could|would) you (?:please )?|please )','',command)
        if command not in ('daily briefing','my daily briefing','give me my daily briefing',
                           'morning briefing','my morning briefing','give me a daily briefing'):
            return {'handled':False}
        now=self._now()
        parts=['Your daily briefing — '+now.strftime('%A, %d %B %Y')+'.']
        spoken=list(parts)
        sources=[];partial=False
        try:
            location=self._everyday.location()['location']
            if not location:
                weather='Set your weather city in Settings → Everyday to include a forecast.'
            else:
                weather=self._everyday.execute('weather today')['reply']
                if 'Source: Open-Meteo.' in weather:
                    sources.append({'name':'Open-Meteo','url':'https://open-meteo.com/'})
                else:partial=True
            parts.append('Weather: '+weather)
            spoken.append('Weather: '+weather.partition('Data time:')[0].strip())
        except Exception:
            partial=True
            parts.append('Weather is unavailable right now.')
            spoken.append(parts[-1])
        try:
            items=self._reminders.pending()
            overdue=[item for item in items if item['due']<=now.timestamp()]
            today=[item for item in items if item['due']>now.timestamp()
                   and datetime.fromtimestamp(item['due'],now.tzinfo).date()==now.date()]
            for title,group in (('Overdue reminders',overdue),('Upcoming today',today)):
                lines=[title+': '+str(len(group))+'.']
                for item in group[:5]:
                    date=datetime.fromtimestamp(item['due'],now.tzinfo)
                    lines.append('Reminder '+str(item['id'])+' — '+date.isoformat(timespec='minutes')+': '+item['text'])
                if len(group)>5:lines.append('Say “show reminders” for the remaining '+str(len(group)-5)+'.')
                section='\n'.join(lines)
                parts.append(section);spoken.append(section)
        except Exception:
            partial=True
            parts.append('Reminders are unavailable right now; this does not mean you have none.')
            spoken.append(parts[-1])
        if self._calendar is not None:
            try:
                if not self._calendar.calendars():section='Calendar: import an .ics file in Settings → Calendar to include events.'
                else:
                    events=self._calendar.today(now)
                    section='Calendar today (imported snapshots): '+str(len(events))+' events.'
                    for event in events[:5]:
                        section+='\n'+event['time']+' — '+event['summary']+(' · '+event['location'] if event['location'] else '')+' [Calendar '+str(event['calendar_id'])+']'
                    if len(events)>5:section+='\nSay “calendar today” to see more.'
                parts.append(section);spoken.append(section)
            except Exception:
                partial=True;parts.append('Calendar is unavailable; this does not mean you have no events.');spoken.append(parts[-1])
        speech=' '.join(spoken)
        if len(speech)>4800:speech=speech[:4700].rsplit(' ',1)[0]+'. More details are shown in chat.'
        return {'handled':True,'ok':True,'partial':partial,'reply':'\n\n'.join(parts),
                'spoken_reply':speech,'sources':sources}
