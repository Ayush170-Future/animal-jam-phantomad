"""Build PhantomFall.webp and PhantomFlames.webp from the extracted game
assets. Output sheets:
  PhantomFall:    6 cols x 3 rows, 115x95 each  (6 anim frames per variant,
                  3 variants). Source frames vary 107-115 x 89-95; we center
                  them in the max-size cell.
  PhantomFlames:  7 cols x 1 row, 60x112 each   (single-row strip)
"""
from pathlib import Path
from PIL import Image

EXTRACTED = Path("/Users/ayushsingh/Documents/programming/animal-jam-ad/"
                 "extracted/FallingPhantoms")
BUILD_ASSETS = Path("/Users/ayushsingh/Documents/programming/"
                    "animal-jam-ad/build/assets")
BUILD_SPRITES = Path("/Users/ayushsingh/Documents/programming/"
                     "animal-jam-ad/build/sprites")

FALL_CELL_W = 115
FALL_CELL_H = 95
FALL_FRAMES = 6
FALL_VARIANTS = 3
FLAME_CELL_W = 60
FLAME_CELL_H = 112
FLAME_FRAMES = 7


def build_fall():
    sheet = Image.new(
        "RGBA",
        (FALL_CELL_W * FALL_FRAMES, FALL_CELL_H * FALL_VARIANTS),
        (0, 0, 0, 0),
    )
    for v in range(1, FALL_VARIANTS + 1):
        for f in range(1, FALL_FRAMES + 1):
            p = EXTRACTED / "largePhantomFallAnim" / \
                f"largePhantomFallAnim{v}_{f:04d}.png"
            img = Image.open(p).convert("RGBA")
            iw, ih = img.size
            x = (f - 1) * FALL_CELL_W + (FALL_CELL_W - iw) // 2
            y = (v - 1) * FALL_CELL_H + (FALL_CELL_H - ih) // 2
            sheet.paste(img, (x, y), img)
    BUILD_SPRITES.mkdir(parents=True, exist_ok=True)
    BUILD_ASSETS.mkdir(parents=True, exist_ok=True)
    sheet.save(BUILD_SPRITES / "PhantomFall.png", "PNG", optimize=True)
    sheet.save(BUILD_ASSETS / "PhantomFall.webp", quality=92, method=6)
    return BUILD_ASSETS / "PhantomFall.webp"


def build_flames():
    sheet = Image.new(
        "RGBA",
        (FLAME_CELL_W * FLAME_FRAMES, FLAME_CELL_H),
        (0, 0, 0, 0),
    )
    for f in range(1, FLAME_FRAMES + 1):
        p = EXTRACTED / "phantomFlamesAnim" / \
            f"phantomFlamesAnim_{f:04d}.png"
        img = Image.open(p).convert("RGBA")
        iw, ih = img.size
        x = (f - 1) * FLAME_CELL_W + (FLAME_CELL_W - iw) // 2
        y = (FLAME_CELL_H - ih) // 2
        sheet.paste(img, (x, y), img)
    sheet.save(BUILD_SPRITES / "PhantomFlames.png", "PNG", optimize=True)
    sheet.save(BUILD_ASSETS / "PhantomFlames.webp", quality=92, method=6)
    return BUILD_ASSETS / "PhantomFlames.webp"


if __name__ == "__main__":
    fp = build_fall()
    print(f"wrote {fp} ({fp.stat().st_size/1024:.1f} KB)")
    fp = build_flames()
    print(f"wrote {fp} ({fp.stat().st_size/1024:.1f} KB)")
