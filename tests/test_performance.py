from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app/desktop'))
from performance_log import PerformanceLog

log=PerformanceLog(limit=4)
assert log.snapshot()['retained']==0
log.record('chat','completed',2,first_text_seconds=.2,prompt='must not be retained')
log.record('chat','cancelled',8,first_text_seconds=.4)
snapshot=log.snapshot();chat=snapshot['summary'][0]
assert chat['count']==2 and chat['completed']==1 and chat['mean_seconds']==2
assert 'prompt' not in str(snapshot) and 'must not' not in str(snapshot)
log.record('chat','completed',float('nan'))
log.record('other','completed',1)
assert log.snapshot()['retained']==2
snapshot['recent'][0]['total_seconds']=100
assert log.snapshot()['recent'][0]['total_seconds']==8
with ThreadPoolExecutor(max_workers=4) as pool:
    list(pool.map(lambda n:log.record('speech','completed',n,synthesis_seconds=n/2),range(20)))
assert log.snapshot()['retained']==4
log.clear();assert log.snapshot()['retained']==0
print('PASS: bounded timing history, completed-only averages, concurrency, snapshots and content exclusion')
