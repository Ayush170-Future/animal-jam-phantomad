"""Align new fox frames and build a tail-wag GIF.

Strategy:
  1. Crop each frame to the fox bbox (non-black pixels).
  2. Detect the black tail-tuft's X-centroid within the upper portion of the
     fox bbox.
  3. Sort frames by tail-X, then ping-pong (L -> R -> L) for a smooth wag.
  4. Composite onto a uniform canvas anchored on the body center, not the bbox
     center, so the tail moving sideways doesn't shift the whole body.
"""
from pathlib import Path
from PIL import Image

SRC = Path(__file__).parent
ALIGNED = SRC / "aligned2"
ALIGNED.mkdir(exist_ok=True)
OUT_GIF = SRC / "fox_wag.gif"

BG_THRESHOLD = 30          # below this -> background
TUFT_DARK_MAX = 110        # tuft pixels are near-black (but not bg, see below)
TUFT_REGION_TOP = 0.0
TUFT_REGION_BOTTOM = 0.45  # tuft lives in the top ~45% of the fox bbox
PAD = 20
FRAME_MS = 130

files = sorted(p for p in SRC.glob("image*.png"))


def fox_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    gray = img.convert("L")
    mask = gray.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("no foreground found")
    return bbox


def body_anchor_x(crop: Image.Image) -> int:
    """X of the body's horizontal center — measured in the LOWER half of the
    crop where the standing body/legs dominate, ignoring the swinging tail."""
    w, h = crop.size
    gray = crop.convert("L")
    lower = gray.crop((0, h // 2, w, h))
    mask = lower.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bbox = mask.getbbox()
    if bbox is None:
        return w // 2
    return (bbox[0] + bbox[2]) // 2


def tail_x(crop: Image.Image) -> float:
    """Centroid X of dark (tuft) pixels in the upper band of the crop."""
    w, h = crop.size
    y0 = int(h * TUFT_REGION_TOP)
    y1 = int(h * TUFT_REGION_BOTTOM)
    region = crop.crop((0, y0, w, y1))
    px = region.load()
    total_x = 0
    count = 0
    for y in range(region.height):
        for x in range(region.width):
            r, g, b = px[x, y][:3]
            brightness = r + g + b
            # tuft: not background (already cropped to fox), but very dark
            if brightness > BG_THRESHOLD * 3 and max(r, g, b) < TUFT_DARK_MAX:
                total_x += x
                count += 1
    if count == 0:
        return w / 2
    return total_x / count


# 1. Crop + measure
crops = []  # (path, cropped_img, body_cx, tail_cx)
for f in files:
    im = Image.open(f).convert("RGB")
    bbox = fox_bbox(im)
    crop = im.crop(bbox)
    body_cx = body_anchor_x(crop)
    t_cx = tail_x(crop)
    crops.append((f, crop, body_cx, t_cx))
    print(f"{f.name:24s}  body_cx={body_cx:4d}  tail_cx={t_cx:6.1f}  "
          f"tail_offset={t_cx - body_cx:+6.1f}")

# 2. Sort by tail offset (relative to body center), then ping-pong
crops_sorted = sorted(crops, key=lambda c: c[3] - c[2])
n = len(crops_sorted)
# ping-pong: leftmost -> rightmost -> back toward leftmost, no repeats at ends
order = list(range(n)) + list(range(n - 2, 0, -1))
sequence = [crops_sorted[i] for i in order]

print("\nWag sequence:")
for c in sequence:
    print(f"  {c[0].name}  (offset {c[3] - c[2]:+.1f})")

# 3. Canvas sized to the largest crop, with extra room for tail sweep
max_w = max(c.width for _, c, _, _ in crops)
max_h = max(c.height for _, c, _, _ in crops)
canvas_w = max_w + 2 * PAD
canvas_h = max_h + 2 * PAD
anchor_x = canvas_w // 2  # body center should land here
anchor_y_bottom = canvas_h - PAD  # feet line

frames = []
for i, (f, crop, body_cx, _) in enumerate(sequence):
    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    x = anchor_x - body_cx
    y = anchor_y_bottom - crop.height
    canvas.paste(crop, (x, y))
    canvas.save(ALIGNED / f"{i:02d}_{f.name}")
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

print(f"\ncanvas: {canvas_w}x{canvas_h}")
print(f"frames: {len(frames)} (ping-pong over {n} unique)")
print(f"gif:    {OUT_GIF}")
