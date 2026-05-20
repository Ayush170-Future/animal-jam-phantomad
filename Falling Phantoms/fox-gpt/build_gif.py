"""Align fox-gpt frames on a common canvas and build a looping GIF."""
from pathlib import Path
from PIL import Image, ImageChops

SRC = Path(__file__).parent
ALIGNED = SRC / "aligned"
ALIGNED.mkdir(exist_ok=True)
OUT_GIF = SRC / "fox.gif"

# Treat near-black as background. Threshold chosen to ignore JPEG/PNG noise.
BG_THRESHOLD = 30
PAD = 16  # breathing room around the fox on the final canvas
FRAME_MS = 150  # per-frame duration in the gif

files = sorted(p for p in SRC.glob("*.png") if p.name != "fox.gif")

def fox_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    """Bounding box of non-black pixels."""
    gray = img.convert("L")
    mask = gray.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("no foreground found")
    return bbox

crops = []
for f in files:
    im = Image.open(f).convert("RGB")
    bbox = fox_bbox(im)
    crops.append((f, im.crop(bbox)))

max_w = max(c.width for _, c in crops)
max_h = max(c.height for _, c in crops)
canvas_w = max_w + 2 * PAD
canvas_h = max_h + 2 * PAD

frames = []
for f, c in crops:
    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    # Center horizontally, bottom-align vertically so feet stay on one baseline.
    x = (canvas_w - c.width) // 2
    y = canvas_h - PAD - c.height
    canvas.paste(c, (x, y))
    out_path = ALIGNED / f.name
    canvas.save(out_path)
    frames.append(canvas)

frames[0].save(
    OUT_GIF,
    save_all=True,
    append_images=frames[1:],
    duration=FRAME_MS,
    loop=0,
    optimize=True,
    disposal=2,
)

print(f"canvas: {canvas_w}x{canvas_h}")
print(f"frames: {len(frames)}")
print(f"aligned pngs: {ALIGNED}")
print(f"gif: {OUT_GIF}")
