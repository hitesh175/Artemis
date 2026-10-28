from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import Mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from task_plans import TaskPlans
from tool_router import ToolRouter,Tool
from everyday import Everyday

apps=Mock();apps.execute.return_value={'handled':True,'launched':True,'reply':'Opened Example.'}
router=Mock();router.execute.return_value={'handled':True,'ok':True,'reply':'A result'}
now=[100]
plans=TaskPlans(router,apps,clock=lambda:now[0])
preview=plans.plan('plan tasks: what time is it; calculate 25 * 4; open Example')
token=preview['task_plan']['token']
assert preview['task_plan']['phase']=='preview'
router.execute.assert_not_called();apps.execute.assert_not_called()
assert plans.run(token)['task_plan']['phase']=='completed'
assert router.execute.call_count==2 and apps.execute.call_count==1
plans.run(token);plans.confirm_app(token)
assert apps.execute.call_count==1,'Plan execution must not replay actions'
for text in ('plan tasks: open Example; what time is it','plan tasks: remember that a fact; what time is it',
             'plan tasks: open Example','plan tasks: calculate 2; remove calendar 1',
             'plan tasks: calculate 2; open Notepad and Calculator','plan tasks: calculate 2; cmd /c whoami'):
    assert not plans.plan(text)['ok'],text
assert not plans.plan('explain task planning')['handled']
apps.execute.reset_mock();router.execute.return_value={'handled':True,'ok':False,'reply':'Weather failed'}
token=plans.plan('plan tasks: weather today; open Example')['task_plan']['token']
assert plans.run(token)['task_plan']['phase']=='failed'
apps.execute.assert_not_called()
router.execute.return_value={'handled':True,'ok':True,'reply':'OK'}
apps.execute.return_value={'handled':True,'reply':'Did you mean Example?','confirmation':{'token':'private-app-token','name':'Example'}}
apps.confirm.return_value={'ok':True,'reply':'Opened Example.'}
token=plans.plan('plan tasks: what time is it; open Example')['task_plan']['token']
result=plans.run(token)
assert result['task_plan']['phase']=='needs_confirmation' and 'private-app-token' not in str(result)
assert plans.confirm_app(token)['task_plan']['phase']=='completed'
apps.confirm.assert_called_once_with('private-app-token')
plans.confirm_app(token);assert apps.confirm.call_count==1
token=plans.plan('plan tasks: what time is it; open Example')['task_plan']['token']
plans.run(token);assert plans.cancel(token)['task_plan']['phase']=='cancelled'
apps.cancel_confirmation.assert_called_with('private-app-token')
token=plans.plan('plan tasks: what time is it; open Example')['task_plan']['token']
now[0]+=301
assert plans.run(token)['task_plan']['phase']=='expired'
entered=threading.Event();release=threading.Event()
def execute(_):entered.set();release.wait(3);return {'handled':True,'ok':True,'reply':'Finished current read'}
router.execute.side_effect=execute;apps.execute.reset_mock()
token=plans.plan('plan tasks: weather today; open Example')['task_plan']['token']
responses=[]
worker=threading.Thread(target=lambda:responses.append(plans.run(token)));worker.start()
assert entered.wait(2)
assert plans.run(token)['task_plan']['phase']=='running'
assert plans.cancel(token)['task_plan']['cancelling']
release.set();worker.join(3)
assert responses[0]['task_plan']['phase']=='cancelled';apps.execute.assert_not_called()
with tempfile.TemporaryDirectory() as folder:
    everyday=Everyday(Path(folder)/'weather.json')
    actual=TaskPlans(ToolRouter([Tool('everyday','',everyday.execute)]),apps)
    for text in ('plan tasks: weather today; open Example','plan tasks: calculate 1 / 0; open Example'):
        token=actual.plan(text)['task_plan']['token']
        assert actual.run(token)['task_plan']['phase']=='failed'
    token=actual.plan('plan tasks: calculate 25 * 4; what time is it')['task_plan']['token']
    assert actual.run(token)['task_plan']['phase']=='completed'
    apps.execute.assert_not_called()
print('PASS: reviewed-only plans, bounded steps, single execution, failure/cancellation before launch, expiring confirmations and real tool outcomes')
