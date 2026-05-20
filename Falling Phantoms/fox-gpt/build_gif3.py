"""Crop foxes 1-10 from the labeled sheet, align them, and build a GIF.

The sheet 'full photo.png' is a 5x2 grid of numbered fox poses (1-10, reading
left-to-right, top-to-bottom). We:
  1. Find each fox by connected-component-style bbox detection on a black
     background -- but the white digit labels also contrast against black, so
     instead we slice the sheet into 10 equal cells, then find the fox bbox
     within each cell (top portion only, to skip the white digit).
  2. Align by body center, bottom-anchor on feet.
  3. Report detected tail offset per frame so we can compare to the labeled
     order.
  4. Build a GIF in label order (1 -> 10), looping.
"""
from pathlib import Path
from PIL import Image

SRC = Path(__file__).parent
SHEET = SRC / "full photo.png"
CELLS = SRC / "cells"
ALIGNED = SRC / "aligned3"
CELLS.mkdir(exist_ok=True)
ALIGNED.mkdir(exist_ok=True)
OUT_GIF = SRC / "fox_wag.gif"

COLS, ROWS = 5, 2
BG_THRESHOLD = 30
TUFT_DARK_MAX = 110
PAD = 24
FRAME_MS = 140
# Bottom strip of each cell holds the printed digit label -- skip it when
# finding the fox bbox so the digit doesn't bias bottom alignment.
CELL_TOP_FRAC = 0.04
CELL_BOTTOM_FRAC = 0.78  # only look at top 78% of each cell for the fox


def fox_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    gray = img.convert("L")
    mask = gray.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("no foreground")
    return bbox


def body_anchor_x(crop: Image.Image) -> int:
    w, h = crop.size
    lower = crop.convert("L").crop((0, h // 2, w, h))
    mask = lower.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bb = mask.getbbox()
    return (bb[0] + bb[2]) // 2 if bb else w // 2


def tail_offset(crop: Image.Image, body_cx: int) -> float:
    w, h = crop.size
    region = crop.crop((0, 0, w, int(h * 0.45)))
    px = region.load()
    tx, n = 0, 0
    for y in range(region.height):
        for x in range(region.width):
            r, g, b = px[x, y][:3]
            if r + g + b > BG_THRESHOLD * 3 and max(r, g, b) < TUFT_DARK_MAX:
                tx += x
                n += 1
    if n == 0:
        return 0.0
    return (tx / n) - body_cx


sheet = Image.open(SHEET).convert("RGB")
SW, SH = sheet.size
cell_w = SW // COLS
cell_h = SH // ROWS

crops = []  # (label, cropped fox, body_cx, tail_offset)
for idx in range(COLS * ROWS):
    col = idx % COLS
    row = idx // COLS
    label = idx + 1
    cell = sheet.crop((col * cell_w, row * cell_h,
                       (col + 1) * cell_w, (row + 1) * cell_h))
    # Restrict to the fox region of the cell (skip digit label area).
    cw, ch = cell.size
    fox_region = cell.crop((0, int(ch * CELL_TOP_FRAC),
                            cw, int(ch * CELL_BOTTOM_FRAC)))
    bb = fox_bbox(fox_region)
    fox = fox_region.crop(bb)
    fox.save(CELLS / f"{label:02d}.png")
    body_cx = body_anchor_x(fox)
    t_off = tail_offset(fox, body_cx)
    crops.append((label, fox, body_cx, t_off))
    print(f"  {label:2d}: size={fox.size}  body_cx={body_cx}  "
          f"tail_offset={t_off:+.1f}")

# Build canvas
max_w = max(c.width for _, c, _, _ in crops)
max_h = max(c.height for _, c, _, _ in crops)
canvas_w = max_w + 2 * PAD
canvas_h = max_h + 2 * PAD
anchor_x = canvas_w // 2
anchor_y_bottom = canvas_h - PAD

frames = []
for label, fox, body_cx, _ in crops:
    canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
    canvas.paste(fox,
                 (anchor_x - body_cx, anchor_y_bottom - fox.height))
    canvas.save(ALIGNED / f"{label:02d}.png")
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
print(f"gif:    {OUT_GIF}")
