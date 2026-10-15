"""One-time transfer of generated pigment, retaining ancestral wall pixels."""
import hashlib
import json
from pathlib import Path
from image_bytes import read_png, png, resize, jpeg

base = Path('artifacts/line-2/wall.png')
output = Path('artifacts/line-2/wall-v14.png')
ancestor = base.read_bytes()
assert hashlib.sha256(ancestor).hexdigest() == '2c5ba4f206a32ad52f4566e05279e84ebf96e4b43ff4710bc44aeec4f8a794f6'
w, h, old = read_png(ancestor)
draft = output.read_bytes()
dw, dh, generated = read_png(draft)
assert (w, h) == (1254, 1254)
assert (dw, dh) == (1024, 1024)
# Only the generated motif's pigment is transferred. Its flat generated stone
# is discarded; all ancestral pixels outside this vacant patch stay exact.
cx, cy, cw, ch = 300, 280, 450, 430
x0, y0, width, height = 65, 420, 140, 125
final = bytearray(old)
changed = 0
for y in range(y0, y0 + height):
    for x in range(x0, x0 + width):
        i = (y*w+x)*3
        rock = old[i:i+3]
        sx = cx + (x-x0)*cw//width
        sy = cy + (y-y0)*ch//height
        j = (sy*dw+sx)*3
        r, g, b = generated[j:j+3]
        # Leave deep cracks untouched and let rock texture show through pigment.
        if max(rock) < 85 or (x*19+y*31)%23 == 0:
            continue
        charcoal = max(r, g, b) < 115 and sum(rock)-r-g-b > 50
        chalk = r > 195 and g > 180 and b > 135 and 645 < sx < 685 and 530 < sy < 570
        if charcoal or chalk:
            pigment = (42, 30, 20) if charcoal else (208, 193, 151)
            alpha = .72 if charcoal else .64
            for c in range(3):
                final[i+c] = round(rock[c]*(1-alpha) + pigment[c]*alpha)
            changed += final[i:i+3] != old[i:i+3]
assert 500 < changed < width*height
for y in range(h):
    for x in range(w):
        i = (y*w+x)*3
        if final[i:i+3] != old[i:i+3]:
            assert x0 <= x < x0+width and y0 <= y < y0+height
            assert max(old[i:i+3]) >= 85
encoded = png(w, h, final)
base.write_bytes(encoded)
output.write_bytes(encoded)
preview = jpeg(512, 512, resize(w, h, final), 52)
assert len(preview) < 100000
Path('dist/line-2/34.jpg').write_bytes(preview)
review = {
    'number': 34, 'ancestor_sha256': hashlib.sha256(ancestor).hexdigest(),
    'sha256': hashlib.sha256(encoded).hexdigest(),
    'wall': {'paths': [str(base), str(output)], 'width': w, 'height': h,
             'format': 'PNG', 'mode': 'RGB', 'bytes': len(encoded)},
    'preview': {'path': 'dist/line-2/34.jpg', 'width': 512, 'height': 512,
                'format': 'JPEG', 'bytes': len(preview)},
    'addition_region': {'x': x0, 'y': y0, 'width': width, 'height': height},
    'changed_pixels': changed, 'unchanged_pixels': w*h-changed,
    'outside_region_pixel_identical': True, 'dark_cracks_preserved': True,
    'generation_tool': 'mcp__image__generate_image',
    'draft_sha256': hashlib.sha256(draft).hexdigest(),
    'generated_dimensions': [dw, dh], 'draft_retained': False,
    'visual_review': 'pending inspection', 'unmet_visual_requirements': []}
Path('line-2/wall-review-34.json').write_text(json.dumps(review, indent=2)+'\n')
print(json.dumps(review, indent=2))
