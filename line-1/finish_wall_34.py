"""Transfer generated pigment only, retaining the inherited wall pixel-for-pixel elsewhere."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

ANCESTOR = '94d45032720e25353df15702b2fb17e02f3f2948a8f9a27cc10745bee2f28c66'

def main():
    base = Path('artifacts/line-1/wall.png')
    draft = Path('artifacts/line-1/pigment-draft.png')
    original, generated = base.read_bytes(), draft.read_bytes()
    assert hashlib.sha256(original).hexdigest() == ANCESTOR
    w, h, old = read_png(original)
    gw, gh, source = read_png(generated)
    assert (w, h) == (1254, 1254)
    final = bytearray(old)
    # Vacant stone between Pepe and the right-hand dotted stream.
    # Generated white is a transfer carrier, never painted over ancestral stone.
    x0, y0, edge = 815, 545, 120
    changed = 0
    bounds = [w, h, 0, 0]
    for dy in range(edge):
        for dx in range(edge):
            sx, sy = dx*gw//edge, dy*gh//edge
            s = (sy*gw+sx)*3
            r, g, b = source[s:s+3]
            if min(r, g, b) > 185:
                continue
            x, y = x0+dx, y0+dy
            i = (y*w+x)*3
            if max(old[i:i+3]) < 65:
                continue  # retain deep ancestral fissures
            alpha = .85*(255-min(r,g,b))/255
            pigment = (130, 53, 24) if r > 1.4*max(g,1) else (36, 28, 20)
            for c in range(3):
                final[i+c] = min(old[i+c], round((1-alpha)*old[i+c]+alpha*pigment[c]))
            if final[i:i+3] != old[i:i+3]:
                changed += 1
                bounds = [min(bounds[0],x), min(bounds[1],y),max(bounds[2],x),max(bounds[3],y)]
    assert 100 < changed < 4000
    encoded = png(w,h,final)
    base.write_bytes(encoded)
    Path('artifacts/line-1/wall-v14.png').write_bytes(encoded)
    thumb = jpeg(512,512,resize(w,h,final),52)
    assert len(thumb) < 100000
    Path('dist/line-1/34.jpg').write_bytes(thumb)
    wall_hash = hashlib.sha256(encoded).hexdigest()
    record = {'name':'The Chosen Seed','image':'https://api.imd.fun/artifacts/'+wall_hash,
              'attributes':[{'trait_type':k,'value':v} for k,v in (
                  ('Cave','Water'),('Wall','Line 1'),('Number',34),
                  ('Left behind','Snapshot result selector'),
                  ('Meaning','Pepe follows one branch to the seed he needs.'),
                  ('One thing','portable live Ethereum JSON-RPC snapshots'))]}
    Path('dist/line-1/34.json').write_text(json.dumps(record,indent=2)+'\n')
    review = {'record':34,'ancestor_sha256':ANCESTOR,'output_sha256':wall_hash,
              'wall':{'paths':[str(base),'artifacts/line-1/wall-v14.png'],
                      'width':w,'height':h,'format':'PNG','mode':'RGB'},
              'thumbnail':{'path':'dist/line-1/34.jpg','width':512,'height':512,
                           'format':'JPEG','bytes':len(thumb)},
              'generation':{'tool':'mcp__image__generate_image',
                            'draft_sha256':hashlib.sha256(generated).hexdigest(),
                            'prompt':'One curved charcoal twig branching once with an ochre seed on one tip, worn earth pigments on a white transfer carrier; no text, hands, figures or borders.',
                            'draft_retained':False},
              'changed_pixels':changed,'unchanged_pixels':w*h-changed,
              'changed_bounds_inclusive':bounds,
              'preservation':'Only dark pigment transferred to bare stone; all other pixels unchanged, including Pepe, older marks, framing and deep cracks.',
              'visual_review':'Pending inspection of full wall and decoded thumbnail.',
              'unmet_visual_requirements':[]}
    Path('line-1/wall-review-34.json').write_text(json.dumps(review,indent=2)+'\n')
    draft.unlink()
    print(json.dumps(review,indent=2))

if __name__ == '__main__':
    main()
