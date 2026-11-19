"""Assemble the original, registered cat sprites into a lightweight README GIF.

Requires Pillow. Run from any directory: python scripts/gen_support_cat.py
The source sheet and its generation prompt live in assets/support/.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets' / 'support'
sheet = Image.open(ASSETS / 'coffee-cat-sheet.png').convert('RGBA')
assert sheet.size == (1254, 1254), 'Sprite registration expects the original sheet.'

# Actual registered origins in the generated sheet, with 16px breathing room.
# Equal crops keep the face/mug fixed while the tail, eyes and puffs change.
frames = [
    sheet.crop((x, y, x + 288, y + 288)).resize((144, 144), Image.Resampling.NEAREST)
    for y in (33, 343, 653, 953)
    for x in (34, 342, 650, 958)
]

# One shared palette prevents color flicker; GIF index zero is transparency.
atlas = Image.new('RGB', (144 * len(frames), 144), '#202127')
for i, frame in enumerate(frames):
    atlas.paste(frame, (i * 144, 0), frame)
palette_image = atlas.quantize(colors=95, method=Image.Quantize.MEDIANCUT)
colors = palette_image.getpalette()[:95 * 3]
palette = [0, 0, 0] + colors
palette += [0] * (768 - len(palette))
gif_frames = []
for frame in frames:
    indexed = frame.convert('RGB').quantize(palette=palette_image, dither=Image.Dither.NONE)
    pixels = [p + 1 if a >= 128 else 0 for p, a in zip(indexed.tobytes(), frame.getchannel('A').tobytes())]
    out = Image.new('P', frame.size)
    out.putpalette(palette)
    out.putdata(pixels)
    gif_frames.append(out)

# A quick natural blink, a little resting hold, exactly four seconds total.
durations = [600, 250, 250, 250, 250, 250, 90, 120, 90, 350, 250, 250, 250, 250, 250, 250]
assert sum(durations) == 4000
gif_frames[0].save(
    ASSETS / 'coffee-cat.gif', save_all=True, append_images=gif_frames[1:],
    duration=durations, loop=0, transparency=0, disposal=2, optimize=True,
)
frames[0].save(ASSETS / 'coffee-cat.png', optimize=True)

with Image.open(ASSETS / 'coffee-cat.gif') as gif:
    total = 0
    for i in range(gif.n_frames):
        gif.seek(i)
        total += gif.info['duration']
    assert gif.n_frames == 16 and total == 4000 and gif.info['loop'] == 0
    print(f'{gif.n_frames} frames, {total}ms, {gif.size}, {(ASSETS / "coffee-cat.gif").stat().st_size:,} bytes')
