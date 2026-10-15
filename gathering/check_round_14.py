#!/usr/bin/env python3
"""Exercise new interfaces, explicit rejections and portable settlement gate."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
BASE = 'shared/settlement-gate/'
PIN = '751fa0b816bfee7a209166f8844365b629bcc5a0bbedf090dd9b3755f330f5db'
DEMO = [BASE+'gate.py', BASE+'baseline.json', BASE+'baseline.json', '--baseline-sha256', PIN]


def main():
    assert Path.cwd() == ROOT
    scratch = ROOT/'test/scratch/round14'
    scratch.mkdir(parents=True,exist_ok=True)
    detached = scratch/'portable'
    shutil.copytree(ROOT/BASE,detached/BASE,dirs_exist_ok=True)
    old = json.loads((ROOT/BASE/'baseline.json').read_text())
    weak = json.loads(json.dumps(old)); weak['items'][0]['policy']['requireFinalized'] = False
    strict = json.loads(json.dumps(old)); strict['items'][0]['policy']['minimumConfirmations'] = 1000000
    for name,plan in [('weaker',weak),('stricter',strict)]:
        (scratch/(name+'.json')).write_text(json.dumps(plan)+'\n')
    cases=[
        (ROOT,0,[BASE+'test_gate.py'],None),
        (ROOT,0,DEMO,BASE+'example-match.json'),
        (ROOT,1,[BASE+'gate.py',BASE+'baseline.json',str((scratch/'weaker.json').relative_to(ROOT)),
                 '--baseline-sha256',PIN],BASE+'example-plan-rejection.json'),
        (ROOT,2,[BASE+'gate.py',BASE+'baseline.json',str((scratch/'stricter.json').relative_to(ROOT)),
                 '--baseline-sha256',PIN],BASE+'example-evidence-rejection.json'),
        (detached,0,[BASE+'test_gate.py'],None),
        (detached,0,DEMO,None),
        (ROOT,1,['line-2/tools/sarif-review/review.py','line-2/tools/json-contract/report.contract.json',
                 'line-2/tools/rule-locator/report.invalid.json'],'gathering/invalid-review-14.sarif'),
        (ROOT,1,['line-4/tools/array-review/array_review.py','line-4/tools/array-review/zto-reordered.json',
                 '--expect','line-4/tools/array-review/zto-arrays.json','--digest-expect',
                 '0xafd46e38940aa3cad45ccacf9ebbea5686570df15dcbf08e79119502d95605ba'],None),
        (ROOT,1,['line-1/tools/snapshot-select/select_result.py','line-1/tools/snapshot-select/live-block.json',
                 '--pointer','/transactions/999999'],None),
    ]
    rows=[]
    for cwd,expected,args,save in cases:
        done=subprocess.run([sys.executable,'-B',*args],cwd=cwd,capture_output=True,text=True,
            timeout=45,env={'PATH':'/usr/bin:/bin','PYTHONDONTWRITEBYTECODE':'1'})
        row={'command':['python3','-B',*args],'detached':cwd!=ROOT,
             'expectedExit':expected,'exitCode':done.returncode,'passed':done.returncode==expected,
             'stdout':done.stdout,'stderr':done.stderr}
        rows.append(row)
        if save and row['passed']:
            assert len(done.stdout.encode())<=100000
            (ROOT/save).write_text(done.stdout)
        print('PASS' if row['passed'] else 'FAIL',args[0],done.returncode)
    encoded=json.dumps(rows,indent=2)+'\n'
    assert len(encoded.encode())<=100000
    (ROOT/'gathering/round-checks-14.json').write_text(encoded)
    return 0 if all(r['passed'] for r in rows) else 1


if __name__=='__main__':
    raise SystemExit(main())
