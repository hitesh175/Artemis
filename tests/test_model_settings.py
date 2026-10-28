import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from model_settings import ModelSettings

with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'models.sqlite3'
    settings=ModelSettings(path)
    assert settings.get()=='artemis' and not path.exists()
    for invalid in ('',None,'x'*201,'model\nother','$(command)','http://host with spaces'):
        with patch.object(settings,'available') as available:
            try:settings.select(invalid);raise AssertionError('Invalid model accepted')
            except ValueError:pass
            available.assert_not_called()
    with patch.object(settings,'available',return_value=['artemis:latest','example:small']):
        assert settings.select('example:small')=='example:small'
        assert ModelSettings(path).get()=='example:small'
        try:settings.select('missing');raise AssertionError('Missing model accepted')
        except ValueError:pass
        assert settings.get()=='example:small'
        assert settings.select('artemis')=='artemis'
    with patch.object(settings,'available',side_effect=OSError('offline')):
        try:settings.select('example:small');raise AssertionError('Offline selection accepted')
        except OSError:pass
    assert settings.get()=='artemis'
    import model_settings
    data={'models':[{'name':'example:small'},{'name':'example:small'},{'name':'bad model'},None]}
    with patch.object(model_settings.request,'urlopen',return_value=io.BytesIO(json.dumps(data).encode())):
        assert settings.available()==['example:small']
    broken=ModelSettings(Path(folder)/'broken.sqlite3');broken.path.write_bytes(b'broken')
    try:broken.get();raise AssertionError('Corruption silently reset model')
    except Exception as exc:assert not isinstance(exc,AssertionError)
print('PASS: model defaults, persistence, installed-name validation, offline preservation and corrupt settings')
