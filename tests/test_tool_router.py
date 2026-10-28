"""Routing boundaries: no real app launches, audio, network or private state."""
import logging
from pathlib import Path
import sys
import tempfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app/desktop'))
from tool_router import Tool, ToolRouter
from everyday import Everyday
from app_launcher import AppLauncher

first = Mock(return_value={'handled': False})
second = Mock(return_value={'handled': True, 'reply': 'Choose an app.',
                            'confirmation': {'token': 'opaque', 'name': 'Example'}})
router = ToolRouter([Tool('daily', '', first), Tool('apps', '', second)])
result = router.execute('open example')
assert result['confirmation']['token'] == 'opaque'
assert result['spoken_reply'] == result['reply'] and result['tool'] == 'apps'
first.return_value = {'handled': True, 'reply': 'Display', 'spoken_reply': 'Speech',
                      'sources': [{'name': 'Example source'}]}
second.reset_mock()
assert router.execute('weather')['spoken_reply'] == 'Speech'
second.assert_not_called()
for invalid in (None, '', ' ' * 5, 'x' * 3001):
    first.reset_mock()
    assert router.execute(invalid)['ok'] is False
    first.assert_not_called()
for failure in (RuntimeError('failure'), {'handled': True}, {'reply': 'missing flag'}):
    first.side_effect = failure if isinstance(failure, Exception) else None
    first.return_value = failure
    with patch.object(logging.getLogger('tool_router'), 'exception'):
        assert router.execute('open example')['ok'] is False
    second.assert_not_called()
first.side_effect = None
first.return_value = second.return_value = {'handled': False}
assert router.execute('explain gravity')['handled'] is False

with tempfile.TemporaryDirectory() as folder:
    daily = Everyday(Path(folder) / 'weather.json')
    apps = AppLauncher()
    router = ToolRouter([Tool('everyday', '', daily.execute), Tool('apps', '', apps.execute)])
    assert router.execute('calculate (25 + 15) / 2')['reply'].endswith('20')
    assert router.execute('weather today')['tool'] == 'everyday'
    assert not router.execute('explain gravity')['handled']
    with patch('app_launcher.subprocess.Popen') as launch:
        result = router.execute('open Notepad and Calculator')
        assert result['handled'] and not result.get('launched')
        launch.assert_not_called()
    assert apps.confirm('not-a-token')['ok'] is False
print('PASS: tool priority, confirmation preservation, input limits, failure isolation and real handler integration')
