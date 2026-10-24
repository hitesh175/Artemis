"""Localhost-only server with safe Ollama chat proxy. No OS commands or mic access."""
import json, mimetypes
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib import request
from urllib.error import URLError
BASE=Path(__file__).resolve().parent
ROOT=BASE/'web'
SYSTEM='You are Artemis, a concise, warm local Windows AI assistant. The desktop client handles explicit app-opening commands through a separate native router. Users can type or say open Notepad, open Spotify, or launch VS Code. Close app-name matches require an on-screen confirmation. You provide conversation and explanations; never claim to have executed an OS action yourself. The client supports offline Whisper, Isabella speech, Mini mode, and Quiet mode. Do not use emoji unless asked.'
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,fmt,*args):pass
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cross-Origin-Resource-Policy','same-origin')
        super().end_headers()
    def do_GET(self):
        if self.path in ('/api/health','/api/health?'):
            self.reply(200,{'ok':True,'mode':'chat-only','model':'artemis'});return
        if self.path.startswith('/assets/'):
            fname=self.path[len('/assets/'):]
            if fname not in ('lunar_a.png','design_reference.png','orb_native_fallback.png'):
                self.send_error(404);return
            data=(BASE/'assets'/fname).read_bytes()
            self.send_response(200);self.send_header('Content-Type','image/png');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data);return
        super().do_GET()
    def do_POST(self):
        if self.path!='/api/chat':self.send_error(404);return
        try:
            if self.headers.get('Content-Type','').split(';')[0].strip()!='application/json':raise ValueError('Expected JSON')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=35000:raise ValueError('Invalid message size')
            payload=json.loads(self.rfile.read(size))
            message=payload.get('message')
            if not isinstance(message,str) or not 1<=len(message.strip())<=3000:raise ValueError('Message must contain 1–3000 characters')
            history=payload.get('history',[])
            if not isinstance(history,list):raise ValueError('Invalid history')
            safe=[]
            for item in history[-14:]:
                if isinstance(item,dict) and item.get('role') in ('assistant','user') and isinstance(item.get('content'),str):safe.append({'role':item['role'],'content':item['content'][:4000]})
            req_data=json.dumps({'model':'artemis','stream':False,'think':False,'messages':[{'role':'system','content':SYSTEM}]+safe+[{'role':'user','content':message.strip()}],'options':{'num_predict':320}}).encode()
            req=request.Request('http://127.0.0.1:11434/api/chat',data=req_data,headers={'Content-Type':'application/json'},method='POST')
            with request.urlopen(req,timeout=100) as result:response=json.load(result)
            answer=response.get('message',{}).get('content','').strip()
            if not answer:raise RuntimeError('Empty Ollama reply')
            self.reply(200,{'reply':answer})
        except ValueError as exc:self.reply(400,{'error':str(exc)})
        except Exception as exc:self.reply(502,{'error':'Ollama connection failed. Make sure Ollama is running with the artemis model. Detail: '+str(exc)})
    def reply(self,status,payload):
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

def make_server(port=0):return ThreadingHTTPServer(('127.0.0.1',port),Handler)

