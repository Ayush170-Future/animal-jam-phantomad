"""Build FoxIdle spritesheet AND a wag GIF from the manually-cropped cells
in fox-new-gif/. The user has guaranteed each crop includes the full fox
without clipping (especially the paws). Different crops have slightly
different dimensions, so we per-cell:

  1. Knock out black background -> alpha.
  2. Find tight fox bbox (post-knockout).
  3. Body-anchor horizontally (measured from the lower half).
  4. Scale all foxes to a common content height so they appear the same size
     in the animation.
  5. Composite onto a 360x360 cell, matching the OLD FoxIdle footprint:
     24px top pad, 330px content, 6px foot pad.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "Falling Phantoms" / "fox-gpt" / "fox-new-gif"
BUILD = ROOT / "build"
ASSET_DIR = BUILD / "assets"
SPRITE_DIR = BUILD / "sprites"
OUT_PNG = SPRITE_DIR / "FoxIdle.png"
OUT_WEBP = ASSET_DIR / "FoxIdle.webp"
PREVIEW = ROOT / "Falling Phantoms" / "fox-gpt" / "FoxIdle_preview.png"
OUT_GIF = ROOT / "Falling Phantoms" / "fox-gpt" / "fox_wag.gif"

# Frame order = 6-frame ping-pong wag (cell numbers in the labeled sheet).
WAG_ORDER = [6, 2, 4, 5, 10, 7]

# Cell layout — match OLD FoxIdle for clean drop-in.
CELL_PX = 360
TOP_PAD_PX = 24
FOOT_PAD_PX = 6
CONTENT_H_PX = CELL_PX - TOP_PAD_PX - FOOT_PAD_PX  # 330
BG_THRESHOLD = 30
FRAME_MS = 140


def knock_out_background(cell: Image.Image) -> Image.Image:
    """Black background -> transparent via flood-fill from the corners, so
    dark fox features (tail tuft, eyes) are preserved."""
    rgba = cell.convert("RGBA")
    w, h = rgba.size
    gray = cell.convert("L")
    dark = gray.point(lambda v: 0 if v < 25 else 255, mode="L")
    flood = dark.copy()
    for corner in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)]:
        if flood.getpixel(corner) == 0:
            ImageDraw.floodfill(flood, corner, 128, thresh=20)
    bg_mask = flood.point(lambda v: 255 if v == 128 else 0, mode="L")
    alpha = bg_mask.point(lambda v: 0 if v == 255 else 255, mode="L")
    alpha = alpha.filter(ImageFilter.GaussianBlur(radius=0.7))
    rgba.putalpha(alpha)
    return rgba


def fox_bbox(rgba: Image.Image) -> tuple[int, int, int, int]:
    """Robust fox bbox. The user's manual crops sometimes have stray noise
    pixels at the edges (a single row of bright noise can throw off vertical
    sizing). We:
      - Take the raw alpha bbox.
      - Then trim top/bottom rows whose content span is < 25 px (noise rows).
        Real fox content (ears, paws, tuft) spans at least that wide somewhere.
    """
    alpha = rgba.split()[-1]
    alpha_px = alpha.load()
    w, h = alpha.size
    NOISE_SPAN = 25

    def row_span(y: int) -> int:
        first = -1
        last = -1
        for x in range(w):
            if alpha_px[x, y] > 16:
                if first < 0:
                    first = x
                last = x
        return last - first if first >= 0 else -1

    # Find first row from top with span >= NOISE_SPAN.
    top = 0
    while top < h and row_span(top) < NOISE_SPAN:
        top += 1
    # Find last such row from bottom.
    bottom = h - 1
    while bottom > top and row_span(bottom) < NOISE_SPAN:
        bottom -= 1
    if top >= bottom:
        raise ValueError("empty image after noise trim")

    band = rgba.crop((0, top, w, bottom + 1))
    band_alpha = band.split()[-1]
    band_mask = band_alpha.point(lambda v: 255 if v > 8 else 0, mode="L")
    bb = band_mask.getbbox()
    if bb is None:
        raise ValueError("empty band")
    return bb[0], top + bb[1], bb[2], top + bb[3]


def body_anchor_x(fox_rgba: Image.Image) -> int:
    """Body's horizontal center from the lower half (ignores tail sweep)."""
    w, h = fox_rgba.size
    alpha = fox_rgba.split()[-1]
    lower = alpha.crop((0, h // 2, w, h))
    mask = lower.point(lambda v: 255 if v > 8 else 0, mode="L")
    bb = mask.getbbox()
    return (bb[0] + bb[2]) // 2 if bb else w // 2


def head_top_y(fox_rgba: Image.Image) -> int:
    """Find the row where the head (ears+) begins by detecting the first row
    with a wide horizontal span. Above this is just the tail tuft, which has
    a narrow profile."""
    w, h = fox_rgba.size
    alpha = fox_rgba.split()[-1]
    alpha_px = alpha.load()
    # Threshold: row is "wide" if its alpha-content horizontal span exceeds
    # 55% of the fox's overall width.
    wide_threshold = int(w * 0.55)
    for y in range(h):
        first = -1
        last = -1
        for x in range(w):
            if alpha_px[x, y] > 16:
                if first < 0:
                    first = x
                last = x
        if first >= 0 and (last - first) >= wide_threshold:
            return y
    return 0  # fallback


# Target body height (head-top to feet) in cell pixels. Tail extends above.
# Sized so the tallest-tail frame still fits within CONTENT_H_PX above feet.
BODY_TARGET_PX = 280


def fit_into_cell(fox_rgba: Image.Image, body_cx: int, head_y: int) -> Image.Image:
    """Scale fox so 'body height' (head_y -> bottom) maps to BODY_TARGET_PX.
    The tail naturally extends above the body. Paste body-centered, with feet
    on the foot-pad line."""
    fw, fh = fox_rgba.size
    body_h_src = fh - head_y
    if body_h_src <= 0:
        body_h_src = fh
    scale = BODY_TARGET_PX / body_h_src
    # Clamp so the scaled overall height still fits in the cell.
    max_total_h = CELL_PX - FOOT_PAD_PX
    if fh * scale > max_total_h:
        scale = max_total_h / fh
    # And so the scaled width fits.
    if fw * scale > CELL_PX:
        scale = CELL_PX / fw
    new_w = max(1, int(round(fw * scale)))
    new_h = max(1, int(round(fh * scale)))
    scaled = fox_rgba.resize((new_w, new_h), Image.LANCZOS)
    scaled_cx = int(round(body_cx * scale))

    canvas = Image.new("RGBA", (CELL_PX, CELL_PX), (0, 0, 0, 0))
    x = CELL_PX // 2 - scaled_cx
    y = CELL_PX - FOOT_PAD_PX - new_h
    canvas.paste(scaled, (x, y), scaled)
    return canvas


def main():
    frames = []
    print("Processing manual cells:")
    for label in WAG_ORDER:
        src = SRC_DIR / f"cell_{label}.png"
        if not src.exists():
            raise FileNotFoundError(src)
        raw = Image.open(src).convert("RGB")
        rgba = knock_out_background(raw)
        bb = fox_bbox(rgba)
        fox = rgba.crop(bb)
        body_cx = body_anchor_x(fox)
        head_y = head_top_y(fox)
        cell = fit_into_cell(fox, body_cx, head_y)
        frames.append(cell)
        print(f"  cell {label:>2}: raw={raw.size}  fox={fox.size}  "
              f"head_y={head_y}  body_h={fox.size[1]-head_y}  body_cx={body_cx}")

    # Spritesheet
    sheet = Image.new("RGBA", (CELL_PX * len(frames), CELL_PX), (0, 0, 0, 0))
    for i, fr in enumerate(frames):
        sheet.paste(fr, (i * CELL_PX, 0), fr)
    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    OUT_WEBP.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUT_PNG, "PNG", optimize=True)
    sheet.save(OUT_WEBP, "WEBP", quality=90, method=6)

    # Preview with the game's bg colour so we can eyeball alignment.
    preview = Image.new("RGB", sheet.size, (26, 10, 46))
    preview.paste(sheet, (0, 0), sheet)
    preview.save(PREVIEW, "PNG")

    # GIF wag (transparent bg replaced with dark for visibility)
    gif_frames = []
    for fr in frames:
        bg = Image.new("RGB", fr.size, (26, 10, 46))
        bg.paste(fr, (0, 0), fr)
        gif_frames.append(bg)
    gif_frames[0].save(
        OUT_GIF,
        save_all=True,
        append_images=gif_frames[1:],
        duration=FRAME_MS,
        loop=0,
        optimize=True,
        disposal=2,
    )

    print(f"\nwrote {OUT_PNG}  ({OUT_PNG.stat().st_size/1024:.1f} KB)")
    print(f"wrote {OUT_WEBP} ({OUT_WEBP.stat().st_size/1024:.1f} KB)")
    print(f"wrote {OUT_GIF}  ({OUT_GIF.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
