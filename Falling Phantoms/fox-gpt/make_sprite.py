"""Build a 6-frame FoxIdle spritesheet from the labeled sheet and install
it into the game's build/assets and build/sprites directories.

Matches the existing FoxIdle format: 6 frames, 360x360 each, 2160x360 total,
RGBA with transparent background, bottom-aligned with ~6px foot pad."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SRC_SHEET = ROOT / "Falling Phantoms" / "fox-gpt" / "full photo.png"
BUILD = ROOT / "build"
ASSET_DIR = BUILD / "assets"
SPRITE_DIR = BUILD / "sprites"
OUT_PNG = SPRITE_DIR / "FoxIdle.png"
OUT_WEBP = ASSET_DIR / "FoxIdle.webp"
PREVIEW = ROOT / "Falling Phantoms" / "fox-gpt" / "FoxIdle_preview.png"

COLS, ROWS = 5, 2
BG_THRESHOLD = 30
TUFT_DARK_MAX = 110

# Row-scan tuning: a row counts as "fox" if at least MIN_FOX_PIXELS columns
# are brighter than ROW_BRIGHT_THRESHOLD. Anti-aliased digit edges have only a
# handful of bright pixels per row, so this excludes them. After the last
# fox row we tolerate up to GAP_ROWS empty rows before stopping (covers small
# gaps between paws and tail-tip shadow, but not the gap to the digit below).
ROW_BRIGHT_THRESHOLD = 50
MIN_FOX_PIXELS = 12
GAP_ROWS = 8

# Sprite sheet target.
# Match the original FoxIdle's in-cell footprint exactly:
#   top pad 24, bottom pad 6, fox content height 330 (out of 360).
# This keeps the new fox's feet on GROUND_Y while shrinking the body so it
# doesn't overlap the depicted grass strip in the background.
CELL_PX = 360
FOOT_PAD_PX = 6
TOP_PAD_PX = 24
CONTENT_H_PX = CELL_PX - TOP_PAD_PX - FOOT_PAD_PX  # 330
N_FRAMES = 6

# 6-frame wag picked from the 10 cells. Order chosen for a smooth
# left-> right -> left-ish swing that loops cleanly.
# Reference offsets (tail_x - body_x): 1=-25, 2=+3, 4=+14, 5=+37, 10=+21, 7=+4
WAG_ORDER = [6, 2, 4, 5, 10, 7]


def fox_bbox(img: Image.Image) -> tuple[int, int, int, int]:
    gray = img.convert("L")
    mask = gray.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("no foreground")
    return bbox


def find_fox_in_strip(strip: Image.Image) -> tuple[int, int, int, int]:
    """Find the fox bbox inside a sheet cell, excluding the white digit label
    that sits below the fox. Strategy: per-row horizontal span. The fox
    (head/body/paws) spans wide; the digit is narrow text. Top is the first
    row with any content (catches dark tail tuft above the head); bottom is
    the last row whose content span exceeds WIDE_SPAN_PX."""
    gray = strip.convert("L")
    w, h = strip.size
    px = gray.load()
    WIDE_SPAN_PX = 60

    has_any = [False] * h
    has_wide = [False] * h
    for y in range(h):
        first = -1
        last = -1
        for x in range(w):
            if px[x, y] > BG_THRESHOLD:
                if first < 0:
                    first = x
                last = x
        if first < 0:
            continue
        has_any[y] = True
        if last - first >= WIDE_SPAN_PX:
            has_wide[y] = True

    if not any(has_wide):
        raise ValueError("no wide fox content in strip")
    top = has_any.index(True)
    bottom = h - 1 - list(reversed(has_wide)).index(True)
    bottom += 1

    band = strip.crop((0, top, w, bottom))
    band_mask = band.convert("L").point(
        lambda v: 255 if v > BG_THRESHOLD else 0, mode="L"
    )
    bb = band_mask.getbbox()
    if bb is None:
        raise ValueError("empty fox band")
    return bb[0], top + bb[1], bb[2], top + bb[3]


def body_anchor_x(crop: Image.Image) -> int:
    """X of body's horizontal center using the lower half (ignores tail)."""
    w, h = crop.size
    lower = crop.convert("L").crop((0, h // 2, w, h))
    mask = lower.point(lambda v: 255 if v > BG_THRESHOLD else 0, mode="L")
    bb = mask.getbbox()
    return (bb[0] + bb[2]) // 2 if bb else w // 2


def knock_out_background(cell: Image.Image) -> Image.Image:
    """Black background -> transparent, preserving dark fox features
    (eyes, tail tuft) by only removing background-connected black pixels."""
    rgba = cell.convert("RGBA")
    w, h = rgba.size
    gray = cell.convert("L")
    # 0 = dark (background candidate), 255 = bright
    dark = gray.point(lambda v: 0 if v < 25 else 255, mode="L")
    flood = dark.copy()
    # Flood from each corner: corners are background; connected dark = bg.
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 0:
            ImageDraw.floodfill(flood, corner, 128, thresh=20)
    # Pixels at 128 are reachable background; everything else is fox.
    bg_mask = flood.point(lambda v: 255 if v == 128 else 0, mode="L")
    alpha = bg_mask.point(lambda v: 0 if v == 255 else 255, mode="L")
    # Soften edge a touch so it doesn't look stairstepped.
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.7))
    rgba.putalpha(alpha)
    return rgba


def crop_cells(sheet: Image.Image) -> list[tuple[Image.Image, int]]:
    """Return [(cropped_fox_rgba, body_cx)] for cells 1..10 in label order.

    Uses per-row brightness scan to find each fox's true vertical extent,
    stopping above the white digit label so paws/feet are not clipped."""
    sw, sh = sheet.size
    cw = sw // COLS
    ch = sh // ROWS
    out = []
    for idx in range(COLS * ROWS):
        col, row = idx % COLS, idx // COLS
        cell = sheet.crop((col * cw, row * ch, (col + 1) * cw, (row + 1) * ch))
        l, t, r, b = find_fox_in_strip(cell)
        fox = cell.crop((l, t, r, b))
        body_cx = body_anchor_x(fox)
        fox_rgba = knock_out_background(fox)
        out.append((fox_rgba, body_cx))
        print(f"  cell {idx+1}: bbox=({l},{t},{r},{b})  "
              f"size={r-l}x{b-t}  body_cx={body_cx}")
    return out


def fit_into_cell(fox_rgba: Image.Image, body_cx: int) -> Image.Image:
    """Scale fox to fit CONTENT_H_PX vertical room (matching the original
    FoxIdle's body footprint), paste body-centered, bottom-anchored at the
    foot pad line."""
    fw, fh = fox_rgba.size
    scale = min(CONTENT_H_PX / fh, CELL_PX / fw)
    new_w = int(round(fw * scale))
    new_h = int(round(fh * scale))
    scaled = fox_rgba.resize((new_w, new_h), Image.LANCZOS)
    scaled_cx = int(round(body_cx * scale))

    canvas = Image.new("RGBA", (CELL_PX, CELL_PX), (0, 0, 0, 0))
    x = CELL_PX // 2 - scaled_cx
    y = CELL_PX - FOOT_PAD_PX - new_h
    canvas.paste(scaled, (x, y), scaled)
    return canvas


def main():
    sheet = Image.open(SRC_SHEET).convert("RGB")
    cells = crop_cells(sheet)  # index 0..9 == label 1..10

    sheet_out = Image.new("RGBA", (CELL_PX * N_FRAMES, CELL_PX), (0, 0, 0, 0))
    for i, label in enumerate(WAG_ORDER):
        fox_rgba, body_cx = cells[label - 1]
        frame = fit_into_cell(fox_rgba, body_cx)
        sheet_out.paste(frame, (i * CELL_PX, 0), frame)
        print(f"  frame {i}: cell {label}")

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEBP.parent.mkdir(parents=True, exist_ok=True)
    sheet_out.save(OUT_PNG, "PNG", optimize=True)
    sheet_out.save(OUT_WEBP, "WEBP", quality=90, method=6)

    # Save a visible preview on a dark bg for quick inspection.
    preview = Image.new("RGB", sheet_out.size, (26, 10, 46))
    preview.paste(sheet_out, (0, 0), sheet_out)
    preview.save(PREVIEW, "PNG")

    print(f"\nwrote {OUT_PNG}  ({OUT_PNG.stat().st_size/1024:.1f} KB)")
    print(f"wrote {OUT_WEBP} ({OUT_WEBP.stat().st_size/1024:.1f} KB)")
    print(f"preview {PREVIEW}")


if __name__ == "__main__":
    main()
