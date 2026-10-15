#!/usr/bin/env python3
"""Keep ancestor pixels, transferring only the image tool's new knot pigment."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, jpeg, resize

ANCESTOR = '67105ad606c973ffba7651b78d9b8ecf5fdaa34300ac47ab445f260df3e29d07'


def main():
    ancestor_path = Path('artifacts/gathering/wall.png')
    target = Path('artifacts/gathering/wall-v14.png')
    ancestor, draft = ancestor_path.read_bytes(), target.read_bytes()
    assert hashlib.sha256(ancestor).hexdigest() == ANCESTOR
    w,h,old = read_png(ancestor)
    gw,gh,new = read_png(draft)
    assert (w,h) == (gw,gh) == (1254,1254)
    # Generated knot occupies this rectangle. Its surrounding regenerated stone
    # is discarded. Move NEW pigment onto vacant rock above the older red path.
    source = (838,390,977,476)
    dest = (812,278,110,68)
    x0,y0,width,height = dest
    final = bytearray(old)
    changed = 0
    for dy in range(height):
        for dx in range(width):
            sx = source[0]+dx*(source[2]-source[0])//width
            sy = source[1]+dy*(source[3]-source[1])//height
            gi = (sy*w+sx)*3
            rgb = new[gi:gi+3]
            prior = old[gi:gi+3]
            r,g,b = rgb
            red = r > 45 and r > 1.38*g and r-g > 24 and g > 1.15*b
            # Exclude the old stripe, retaining only newly generated red pigment.
            red = red and (r/max(1,sum(rgb)) > prior[0]/max(1,sum(prior)) + .025 or g < prior[1]-25)
            charcoal = max(rgb) < 72 and max(prior) > 100
            if not (red or charcoal):
                continue
            x,y = x0+dx,y0+dy
            oi=(y*w+x)*3; rock=old[oi:oi+3]
            if max(rock) < 55: # Deep cracks remain ancestral even inside the patch.
                continue
            color=(119,48,24) if red else (38,28,20)
            alpha=.72 if red else .67
            for c in range(3):
                final[oi+c]=min(rock[c],round(rock[c]*(1-alpha)+color[c]*alpha))
            if final[oi:oi+3] != rock:
                changed+=1
    assert changed > 500
    for y in range(h):
        for x in range(w):
            i=(y*w+x)*3
            if not (x0 <= x < x0+width and y0 <= y < y0+height) or max(old[i:i+3]) < 55:
                assert final[i:i+3] == old[i:i+3]
    output=png(w,h,final)
    target.write_bytes(output)
    ancestor_path.write_bytes(output)
    thumb=resize(w,h,final)
    quality=52
    preview=jpeg(512,512,thumb,quality)
    while len(preview)>100000:
        quality-=5
        assert quality >= 10
        preview=jpeg(512,512,thumb,quality)
    Path('dist/gathering/14.jpg').write_bytes(preview)
    review={'ancestorSha256':ANCESTOR,'ancestorSize':[w,h],'wallSize':[w,h],
            'wallFormat':'PNG','wallMode':'RGB','wallSha256':hashlib.sha256(output).hexdigest(),
            'generatedDraftSha256':hashlib.sha256(draft).hexdigest(),'generatedDraftRetained':False,
            'sourceRectangle':list(source),'additionRectangle':list(dest),'changedPixels':changed,
            'unchangedPixels':w*h-changed,'allPixelsOutsideAdditionUnchanged':True,
            'deepCracksProtected':True,'previewSize':[512,512],'previewFormat':'JPEG',
            'previewBytes':len(preview),'imageTool':'image_gen.imagegen',
            'prompt':'Preserve every ancestor mark and cave; add one small worn ochre cord knot with charcoal crossing, no hands, words or numbers.',
            'reviewStatus':'requires final visual inspection','unmetVisualRequirements':[]}
    Path('gathering/wall-review-14.json').write_text(json.dumps(review,indent=2)+'\n')
    print(json.dumps(review,indent=2))


if __name__=='__main__':
    main()
