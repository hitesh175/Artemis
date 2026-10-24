"""Deterministic everyday answers; live weather comes only from fixed HTTPS APIs."""
import ast
import json
import math
import operator
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import os

HELP='I can open installed apps, give live weather for your saved city, tell the local date/time, and calculate basic arithmetic. Try: “open Notepad”, “what’s today’s weather?”, “weather tomorrow”, “what time is it?”, or “calculate (25 + 15) / 2”. Use Settings → Everyday for your weather city. Hands-free must be started explicitly; Quiet mode blocks audio.'
CODES={0:'clear sky',1:'mainly clear',2:'partly cloudy',3:'overcast',45:'fog',48:'freezing fog',51:'light drizzle',53:'drizzle',55:'heavy drizzle',56:'freezing drizzle',57:'heavy freezing drizzle',61:'light rain',63:'rain',65:'heavy rain',66:'freezing rain',67:'heavy freezing rain',71:'light snow',73:'snow',75:'heavy snow',77:'snow grains',80:'light rain showers',81:'rain showers',82:'heavy rain showers',85:'snow showers',86:'heavy snow showers',95:'thunderstorms',96:'thunderstorms with hail',99:'thunderstorms with heavy hail'}

def arithmetic(expression):
    if len(expression)>100:raise ValueError('Use a shorter calculation.')
    expression=expression.replace('×','*').replace('÷','/').replace('^','**')
    tree=ast.parse(expression.strip(),mode='eval')
    if sum(1 for _ in ast.walk(tree))>50:raise ValueError('Calculation is too complex.')
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Mod:operator.mod,ast.Pow:operator.pow}
    def visit(node):
        if isinstance(node,ast.Constant) and type(node.value) in (int,float):value=node.value
        elif isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.UAdd,ast.USub)):
            value=visit(node.operand)*(1 if isinstance(node.op,ast.UAdd) else -1)
        elif isinstance(node,ast.BinOp) and type(node.op) in ops:
            a,b=visit(node.left),visit(node.right)
            if isinstance(node.op,ast.Pow) and (abs(b)>12 or abs(a)>1e8):raise ValueError('Exponent is too large.')
            value=ops[type(node.op)](a,b)
        else:raise ValueError('Use numbers, parentheses, and + − * / % ^ only.')
        if isinstance(value,complex) or not math.isfinite(value) or abs(value)>1e15:raise ValueError('Result is outside the supported range.')
        return value
    return visit(tree.body)

class Everyday:
    def __init__(self,path=None):
        self._path=Path(path) if path else Path(__file__).resolve().parent.parent/'data'/'everyday.json'
        self._lock=threading.RLock();self._choices={};self._cache={};self._location=None
        try:
            data=json.loads(self._path.read_text(encoding='utf-8'))
            if isinstance(data,dict) and isinstance(data.get('label'),str) and -90<=data['latitude']<=90 and -180<=data['longitude']<=180:self._location=data
        except (OSError,ValueError,TypeError,KeyError):pass

    @staticmethod
    def _get(host,path,params):
        req=Request('https://'+host+path+'?'+urlencode(params),headers={'User-Agent':'ArtemisDesktop/1.0'})
        with urlopen(req,timeout=12) as response:
            return json.loads(response.read(1000000))

    def find(self,query):
        if not isinstance(query,str) or not 2<=len(query.strip())<=100:return {'ok':False,'error':'Enter a city and country.'}
        try:
            data=self._get('geocoding-api.open-meteo.com','/v1/search',dict(name=query.strip(),count=5,language='en',format='json'))
            choices=[]
            with self._lock:
                self._choices.clear()
                for item in data.get('results',[]):
                    parts=list(dict.fromkeys(str(item[k]) for k in ('name','admin1','country') if item.get(k)))
                    loc=dict(label=', '.join(parts),latitude=float(item['latitude']),longitude=float(item['longitude']))
                    token=uuid.uuid4().hex;self._choices[token]=(time.monotonic()+300,loc)
                    choices.append(dict(token=token,name=loc['label']))
            return {'ok':True,'choices':choices}
        except Exception:return {'ok':False,'error':'Could not look up the city. Check your internet connection and try again.'}

    def select(self,token):
        with self._lock:
            choice=self._choices.pop(token,None) if isinstance(token,str) else None
            if not choice or choice[0]<time.monotonic():return {'ok':False,'reply':'Location choice expired. Search again.'}
            loc=choice[1]
            try:
                self._path.parent.mkdir(parents=True,exist_ok=True)
                tmp=self._path.with_suffix('.tmp');tmp.write_text(json.dumps(loc),encoding='utf-8');os.replace(tmp,self._path)
                self._location=loc;self._cache.clear()
                return {'ok':True,'reply':'Weather location saved: '+loc['label']+'.','location':loc['label']}
            except OSError:return {'ok':False,'reply':'Could not save the weather location.'}

    def location(self):return {'ok':True,'location':self._location['label'] if self._location else ''}

    def _weather(self,tomorrow=False):
        with self._lock:loc=dict(self._location) if self._location else None
        if not loc:return 'Set your weather city in Settings → Everyday first.'
        key=(loc['latitude'],loc['longitude'])
        try:
            cached=self._cache.get(key)
            if cached and time.monotonic()-cached[0]<300:data=cached[1]
            else:
                data=self._get('api.open-meteo.com','/v1/forecast',dict(latitude=loc['latitude'],longitude=loc['longitude'],current='temperature_2m,apparent_temperature,weather_code,wind_speed_10m',daily='weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',timezone='auto',forecast_days=2))
                self._cache[key]=(time.monotonic(),data)
            daily=data['daily'];i=1 if tomorrow else 0
            required=('weather_code','temperature_2m_max','temperature_2m_min','precipitation_probability_max','time')
            if any(len(daily.get(k,[]))<=i or daily[k][i] is None for k in required):raise ValueError('Incomplete forecast')
            if any(data['current'].get(k) is None for k in ('temperature_2m','apparent_temperature','weather_code','wind_speed_10m','time')):raise ValueError('Incomplete current conditions')
            reply=loc['label']+' — '+('tomorrow' if tomorrow else 'today')+' ('+daily['time'][i]+'). '
            if not tomorrow:
                current=data['current']
                reply+=f"Currently {current['temperature_2m']}°C, feels like {current['apparent_temperature']}°C, {CODES.get(current['weather_code'],'conditions unavailable')}. Wind {current['wind_speed_10m']} km/h. "
            reply+=f"Forecast: {CODES.get(daily['weather_code'][i],'conditions unavailable')}; high {daily['temperature_2m_max'][i]}°C, low {daily['temperature_2m_min'][i]}°C; rain chance {daily['precipitation_probability_max'][i]}%. "
            reply+='Data time: '+data['current']['time'].replace('T',' ')+', '+data['timezone']+'. Source: Open-Meteo. https://open-meteo.com/'
            return reply
        except Exception:return 'I could not retrieve live weather. Check your internet connection and try again; I will not guess the forecast.'

    def execute(self,text):
        if not isinstance(text,str):return {'handled':False}
        s=text.casefold().strip(' .?!').replace('’',"'")
        s=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',s)
        if s in ('help','what can you do','list commands','show commands','daily help'):
            reply=HELP
        elif s in ('what time is it','whats the time',"what's the time",'tell me the time','current time'):
            reply='The local time is '+datetime.now().astimezone().strftime('%H:%M %Z')+'.'
        elif s in ("what's today's date",'whats todays date','what is the date','what is today date',"what is today's date",'what day is it','what date is it','today date',"what's the date",'today'):
            reply='Today is '+datetime.now().astimezone().strftime('%A, %d %B %Y')+'.'
        elif re.match(r'^(?:calculate|compute|what is|what\x27s)\s+[-+.(\d]',s):
            expr=re.sub(r'^(?:calculate|compute|what is|what\x27s)\s+','',s)
            try:reply=expr+' = '+format(arithmetic(expr),'.12g')
            except (ValueError,SyntaxError,ZeroDivisionError,OverflowError) as exc:reply='Could not calculate that: '+str(exc)
        elif ((re.search(r'\b(?:weather|forecast)\b',s) and re.match(r'^(?:what|how|tell|show|give|weather|forecast|today|tomorrow)',s) and not re.search(r'\b(?:explain|code|works|history)\b',s)) or re.match(r'^(?:will it rain|is it raining|do i need (?:an? )?umbrella|should i take (?:an? )?umbrella)',s)):
            city=re.search(r'\bin\s+(.+)',s)
            if city:
                query=re.sub(r'\b(?:today|tomorrow|please)\b','',city.group(1)).strip()
                if self._location and query.casefold() in (self._location['label'].split(',')[0].casefold(),self._location['label'].casefold()):
                    return {'handled':True,'reply':self._weather('tomorrow' in s)}
                found=self.find(query)
                if not found['ok']:reply=found['error']
                elif not found['choices']:reply='No matching weather city found. Try city, country.'
                else:return {'handled':True,'reply':'Choose the location below to use for weather, then ask again.','weather_choices':found['choices']}
            elif any(word in s for word in ('week','yesterday','weekend')):reply='I currently support today and tomorrow. Try “weather tomorrow”.'
            else:reply=self._weather('tomorrow' in s)
        else:return {'handled':False}
        return {'handled':True,'reply':reply}
