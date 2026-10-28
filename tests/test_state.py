import importlib.util
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1].joinpath('app/desktop').resolve()))
from desktop_state import DesktopState

with tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'state.json'
    state=DesktopState(path)
    assert state.load()['preferences']['quiet'] is True
    data=state.load()
    data['history']=[dict(role='user',content='<script>literal text</script>'),dict(role='assistant',content='Hello')]
    data['preferences'].update(speed=70,scale=110,quiet=True)
    state.save(data)
    assert DesktopState(path).load()==data
    invalid=state.load();invalid['preferences']['scale']=1000
    try:state.save(invalid);raise AssertionError('Invalid state accepted')
    except ValueError:pass
    assert DesktopState(path).load()==data
    state.save(dict(preferences=data['preferences'],history=[]))
    assert DesktopState(path).load()['history']==[]
    path.write_text('broken',encoding='utf-8')
    assert DesktopState(path).load()['preferences']['quiet'] is True
    print('PASS: defaults, restart persistence, validation, clear, corrupted-state safe defaults')

# Load staged bridge, use an isolated state path; never initialize/play audio.
import desktop_state
original=desktop_state.DesktopState
with tempfile.TemporaryDirectory() as tmp:
    desktop_state.DesktopState=lambda:original(Path(tmp)/'bridge.json')

    spec=importlib.util.spec_from_file_location('quiet_main',str(Path(__file__).resolve().parents[1]/'app/desktop/main.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    b=module.WindowBridge()
    assert b.handle_command('calculate 2 + 3')['reply'].endswith('5')
    assert b.handle_app_command('calculate 2 + 3') == b.handle_command('calculate 2 + 3')
    assert [tool['name'] for tool in b.list_tools()] == ['everyday', 'apps']
    assert b.start_listening()['ok'] is False
    assert b.speak_reply('Must not play')['ok'] is False
    assert b.set_speech_enabled(True)['ok'] is False
    assert b.speech_status()['enabled'] is False
    saved=b.load_desktop_state();saved['preferences']['speed']=80
    assert b.save_desktop_state(saved)['ok'] is True
    assert b.load_desktop_state()['preferences']['speed']==80
    assert all(callable(getattr(b,n)) for n in dir(b) if not n.startswith('_'))
    print('PASS: native quiet guards block microphone and speech; private bridge objects preserved')

