"""Retain only new image-tool pigment; exact ancestor pixels elsewhere."""
import hashlib
import json
from pathlib import Path

from image_bytes import jpeg, png, read_png, resize


def main():
    folder = Path('artifacts/line-4')
    ancestor = (folder/'wall.png').read_bytes()
    generated = (folder/'wall-v14.png').read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == '73bd6c7a85eb1fcaae76af17d5946836386a2d3e1a65d9ee3e5085b2b1b1a0ec'
    assert hashlib.sha256(generated).hexdigest() == '298779aa9946c1d2707e23c4169f83c352418b854be9b29a8a3c30a29c6484f0'
    w, h, old = read_png(ancestor)
    gw, gh, draft = read_png(generated)
    assert (w, h, gw, gh) == (1254, 1254, 1254, 1254)
    final = bytearray(old)
    for y in range(132, 272):
        for x in range(459, 503):
            i = (y*w+x)*3
            original = old[i:i+3]
            if sum(original) < 80:
                continue
            distances = [(x-cx)**2+(y-cy)**2 for cx, cy in ((478,174),(485,214),(480,249))]
            if any(d < 5**2 for d in distances):
                continue  # Keep hollow centers as original rock.
            r, g, b = draft[i:i+3]
            charcoal = (r < 90 and g < 60 and b < 40 and r-g < 48
                        and sum(original)-sum((r,g,b)) > 25)
            ochre = (any(6**2 <= d < 17**2 for d in distances)
                     and r > 1.85*g and r-g > 40)
            if charcoal:
                target = [round(v*.42) for v in original]
            elif ochre:
                target = [round(v*.25+p*.75) for v, p in zip(original, (r,g,b))]
            else:
                continue
            final[i:i+3] = bytes(target)
    changed = 0
    for i in range(0, len(old), 3):
        if old[i:i+3] != final[i:i+3]:
            y, x = divmod(i//3, w)
            assert 459 <= x < 503 and 132 <= y < 272 and sum(old[i:i+3]) >= 80
            changed += 1
    assert 300 < changed < 4000
    wall = png(w,h,final)
    sha = hashlib.sha256(wall).hexdigest()
    preview = jpeg(512,512,resize(w,h,final),52)
    assert len(preview) < 100_000
    for name in ('wall.png','wall-v14.png'):
        (folder/name).write_bytes(wall)
    Path('dist/line-4/34.jpg').write_bytes(preview)
    review = {
        'wall': {'paths':['artifacts/line-4/wall.png','artifacts/line-4/wall-v14.png'],
                 'width':w,'height':h,'format':'PNG','mode':'RGB','bytes':len(wall),'sha256':sha},
        'preview': {'path':'dist/line-4/34.jpg','width':512,'height':512,'format':'JPEG',
                    'bytes':len(preview),'sha256':hashlib.sha256(preview).hexdigest()},
        'ancestorSha256':hashlib.sha256(ancestor).hexdigest(),
        'generatedDraftSha256':hashlib.sha256(generated).hexdigest(),
        'imageTool':'Built-in imagegen, generation 01a13d8e-31cb-7541-b723-d8510857f5dd',
        'prompt':'Preserve the inherited square cave and every painting. Add only a small gently curved vertical charcoal cord threading three hollow red-ochre seed outlines on vacant rock above Pepe, between the old balance and upper chain. Worn earth pigments, bare rock inside seeds. Preserve Pepe and both original five-digit hands. No new hands, figures, writing, numerals, logos, watermarks or frames.',
        'changedPixels':changed,'unchangedPixels':w*h-changed,
        'additionBoundsExclusive':[459,132,503,272],
        'preservation':'Every pixel outside the isolated new pigment is exact ancestor data. Deep fissures and seed interiors are protected. All older paintings, figure, hands, light, water and framing remain.',
        'visualReview':'Pending final inspection.', 'unmetVisualRequirements':[],
        'limitations':['Local inspection is not independent visual certification.',
                       'The small upper-stone motif is subtle in the thumbnail.',
                       'The generated full draft changed surrounding texture; only isolated new pigment was retained.']}
    Path('line-4/wall-review-34.json').write_text(json.dumps(review,indent=2)+'\n')
    record = {'name':'The Ordered Seeds', 'image':'https://api.imd.fun/artifacts/'+sha,
              'attributes':[
                  {'trait_type':'Cave','value':'Water'},
                  {'trait_type':'Wall','value':'Line 4'},
                  {'trait_type':'Number','value':34},
                  {'trait_type':'Left behind','value':'offline EIP-712 array reviewer'},
                  {'trait_type':'Meaning','value':'Pepe threads each seed in the order it was meant to follow.'},
                  {'trait_type':'One thing','value':'offline EIP-712 typed-data digest checking'}]}
    Path('dist/line-4/34.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__ == '__main__':
    main()
