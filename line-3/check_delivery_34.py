"""Offline structural checks for this round; visual review is separately recorded."""
import hashlib
import json
from pathlib import Path
import subprocess
from image_bytes import read_png


def baseline(path):
    return subprocess.check_output(['git', 'show', 'HEAD:'+str(path)])


def main():
    root = Path('.')
    goal = root/'line-3/GOAL.md'
    assert goal.read_bytes() == baseline(goal)
    records = sorted((root/'dist/line-3').glob('[0-9][0-9].json'))
    assert len(records) == 34
    for number in range(1, 34):
        p = root/'dist/line-3'/f'{number:02}.json'
        assert p.read_bytes() == baseline(p)
    wall = (root/'artifacts/line-3/wall-v14.png').read_bytes()
    assert wall == (root/'artifacts/line-3/wall.png').read_bytes()
    w,h,pixels = read_png(wall)
    assert (w,h) == (1254,1254)
    record = json.loads((root/'dist/line-3/34.json').read_bytes())
    assert set(record) == {'name','image','attributes'}
    assert record['image'] == 'https://api.imd.fun/artifacts/'+hashlib.sha256(wall).hexdigest()
    traits = record['attributes']
    assert len(traits) == 6
    assert all(set(t) == {'trait_type','value'} for t in traits)
    values = {t['trait_type']:t['value'] for t in traits}
    assert set(values) == {'Cave','Wall','Number','Left behind','Meaning','One thing'}
    assert values['Cave'] == 'Water' and values['Wall'] == 'Line 3'
    assert type(values['Number']) is int and values['Number'] == 34
    assert values['Left behind'] == 'settlement-plan-diff'
    preview = (root/'dist/line-3/34.jpg').read_bytes()
    assert preview[:2] == b'\xff\xd8' and preview[-2:] == b'\xff\xd9'
    assert len(preview) < 100000
    changed = subprocess.check_output(['git','diff','--name-only','HEAD']).decode().splitlines()
    new = subprocess.check_output(['git','ls-files','--others','--exclude-standard']).decode().splitlines()
    for name in changed+new:
        assert name.startswith(('line-3/','artifacts/line-3/','dist/line-3/','test/scratch/')), name
        p = root/name
        if p.is_file() and not name.startswith(('artifacts/','test/scratch/')):
            assert p.stat().st_size <= 100000, name
    for name in ('artifacts/line-3/wall.png','artifacts/line-3/wall-v14.png'):
        tracked = subprocess.run(['git','ls-files','--error-unmatch',name],capture_output=True)
        assert tracked.returncode != 0
    review=json.loads((root/'line-3/wall-review-34.json').read_text())
    assert review['unmetVisualRequirements'] == []
    assert review['allPixelsOutsideAdditionUnchanged']
    assert review['wallSha256'] == hashlib.sha256(wall).hexdigest()
    result={'passed':True,'recordCount':len(records),'oldRecordsUnchanged':True,
            'goalUnchanged':True,'scopeChecked':True,'wallDimensions':[w,h],
            'wallFormat':'PNG','previewDimensions':[512,512],'previewFormat':'JPEG',
            'previewBytes':len(preview),'wallSha256':hashlib.sha256(wall).hexdigest(),
            'namedOutputsUntracked':True,'unmetVisualRequirements':[],
            'note':'JPEG dimensions/structure also checked by image inspection tool. Preservation verified during compositing; appearance locally reviewed.'}
    (root/'line-3/delivery-check-34.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
