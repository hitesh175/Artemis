"""Exercise HTTP against fake Ollama; never contact the real model."""
import io
import json
from pathlib import Path
import sys
import threading
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
import server

host=server.make_server()
thread=threading.Thread(target=host.serve_forever,daemon=True);thread.start()
base='http://127.0.0.1:'+str(host.server_port)
# Keep a real client function; patch only the server's upstream reference.
def post(payload):
    req=Request(base+'/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
    return urlopen(req,timeout=3)
try:
    for frames,expected in [
        ([{'message':{'content':'Hello'}},{'message':{'content':' world'},'done':True}], 'done'),
        ([{'message':{'content':'partial'}}], 'error'),
        ([{'error':'model missing'}], 'error')]:
        fake=io.BytesIO(b''.join(json.dumps(f).encode()+b'\n' for f in frames))
        with patch.object(server.request,'urlopen',return_value=fake) as upstream:
            with post({'message':'hello','stream':True}) as response:
                events=[json.loads(line) for line in response]
            assert events[-1].get(expected)
            assert json.loads(upstream.call_args.args[0].data)['stream'] is True
    with patch.object(server.request,'urlopen',return_value=io.BytesIO(b'{"message":{"content":"Hello"}}')):
        assert json.load(post({'message':'hello'}))['reply']=='Hello'
    with patch.object(server.request,'urlopen') as upstream:
        try:post({'message':'hello','stream':'yes'});raise AssertionError('Invalid input accepted')
        except HTTPError as error:assert error.code==400
        upstream.assert_not_called()
    for names,expected in [(['artemis:latest'],'ready'),([], 'not installed')]:
        fake=io.BytesIO(json.dumps({'models':[{'name':n} for n in names]}).encode())
        with patch.object(server.request,'urlopen',return_value=fake):
            assert json.load(urlopen(base+'/api/diagnostics'))['model']==expected
    print('PASS: streamed HTTP, failure events, legacy replies, validation and model diagnostics')
finally:
    host.shutdown();host.server_close();thread.join()
