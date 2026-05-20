"""Build GemBag.webp — a 2D sprite approximating the Animal Jam GemBags
3D model (Falling Phantoms/3D Models/Models/GemBags.fbx).

Produces a single-frame transparent PNG + WebP of a cinched burlap sack
with five colored gems poking out the top (matching AJ's gem palette:
red / green / blue / purple / yellow). Output goes to build/sprites and
build/assets so it can be loaded by playable.html alongside other assets.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

BUILD_ASSETS = Path("/Users/ayushsingh/Documents/programming/"
                    "animal-jam-ad/build/assets")
BUILD_SPRITES = Path("/Users/ayushsingh/Documents/programming/"
                     "animal-jam-ad/build/sprites")

SUPERSAMPLE = 4
CELL_W = 128
CELL_H = 128
W = CELL_W * SUPERSAMPLE
H = CELL_H * SUPERSAMPLE

SACK_BROWN = (140, 92, 48, 255)
SACK_DARK  = (92, 56, 26, 255)
SACK_LIGHT = (190, 138, 78, 255)
ROPE       = (210, 175, 110, 255)
ROPE_DARK  = (135, 105, 55, 255)
OUTLINE    = (45, 25, 10, 255)

GEM_COLORS = [
    ((255, 90, 90),   (140, 20, 20)),   # red
    ((90, 220, 110),  (20, 110, 40)),   # green
    ((90, 170, 255),  (20, 70, 160)),   # blue
    ((205, 120, 255), (95, 30, 160)),   # purple
    ((255, 220, 80),  (180, 130, 20)),  # yellow
]


def outline(draw, poly, color=OUTLINE, width=6 * SUPERSAMPLE):
    draw.line(poly + [poly[0]], fill=color, width=width, joint="curve")


def draw_sack(img):
    d = ImageDraw.Draw(img, "RGBA")
    cx = W // 2
    # Sack silhouette: rounded bottom, narrow cinched neck, flared lip at top.
    # Coords roughly normalized to the cell, scaled by SUPERSAMPLE.
    body_top_y    = int(H * 0.40)
    cinch_y       = int(H * 0.34)
    lip_y         = int(H * 0.28)
    body_bot_y    = int(H * 0.92)
    body_half     = int(W * 0.34)
    cinch_half    = int(W * 0.18)
    lip_half      = int(W * 0.26)

    # Drop shadow under the sack
    shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.ellipse(
        [cx - body_half, body_bot_y - int(H * 0.04),
         cx + body_half, body_bot_y + int(H * 0.06)],
        fill=(0, 0, 0, 110),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(8 * SUPERSAMPLE // 2))
    img.alpha_composite(shadow)

    # Main sack body — fat teardrop. Use a polygon with curved-feeling points.
    body = [
        (cx - cinch_half,      cinch_y),
        (cx - body_half,       body_top_y),
        (cx - body_half - 4,   int(H * 0.62)),
        (cx - body_half + 6,   int(H * 0.82)),
        (cx - body_half // 2,  body_bot_y - 4),
        (cx + body_half // 2,  body_bot_y - 4),
        (cx + body_half - 6,   int(H * 0.82)),
        (cx + body_half + 4,   int(H * 0.62)),
        (cx + body_half,       body_top_y),
        (cx + cinch_half,      cinch_y),
    ]
    d.polygon(body, fill=SACK_BROWN)

    # Shading: darker right side, lighter left highlight band.
    shade_right = [
        (cx,                   cinch_y + 4),
        (cx + cinch_half - 4,  cinch_y + 4),
        (cx + body_half,       body_top_y + 4),
        (cx + body_half + 4,   int(H * 0.62)),
        (cx + body_half - 6,   int(H * 0.82)),
        (cx + body_half // 2,  body_bot_y - 6),
        (cx,                   body_bot_y - 6),
    ]
    d.polygon(shade_right, fill=SACK_DARK)

    hi_left = [
        (cx - cinch_half + 6, cinch_y + 8),
        (cx - body_half + 10, body_top_y + 8),
        (cx - body_half + 4,  int(H * 0.60)),
        (cx - body_half // 2 - 6, int(H * 0.78)),
        (cx - body_half // 2 + 2, int(H * 0.84)),
        (cx - cinch_half // 2,    cinch_y + 12),
    ]
    d.polygon(hi_left, fill=SACK_LIGHT)

    # Outline pass for sack body.
    outline(d, body)

    # Stitch line down the middle for that hand-sewn AJ look.
    stitch_color = (60, 35, 15, 255)
    sx = cx
    n_stitches = 9
    for i in range(n_stitches):
        sy = body_top_y + int((body_bot_y - body_top_y) * (i + 0.5) / n_stitches)
        d.line([(sx - 6, sy), (sx + 6, sy)], fill=stitch_color, width=3 * SUPERSAMPLE)

    # Cinched neck (the rope bunched part) — slightly darker oval band.
    d.polygon(
        [
            (cx - cinch_half - 2, cinch_y),
            (cx - cinch_half + 4, cinch_y - int(H * 0.025)),
            (cx + cinch_half - 4, cinch_y - int(H * 0.025)),
            (cx + cinch_half + 2, cinch_y),
        ],
        fill=SACK_DARK,
    )

    # Flared lip above the rope, behind the gems.
    lip = [
        (cx - cinch_half + 2, cinch_y - 2),
        (cx - lip_half,       lip_y),
        (cx - lip_half + 8,   lip_y - int(H * 0.02)),
        (cx + lip_half - 8,   lip_y - int(H * 0.02)),
        (cx + lip_half,       lip_y),
        (cx + cinch_half - 2, cinch_y - 2),
    ]
    d.polygon(lip, fill=SACK_BROWN)
    outline(d, lip)

    # Rope tie — two short ribbons + a knot dot, drawn in front of cinch.
    rope_y = cinch_y - int(H * 0.005)
    d.line(
        [(cx - cinch_half - 6, rope_y), (cx + cinch_half + 6, rope_y)],
        fill=ROPE, width=8 * SUPERSAMPLE,
    )
    d.line(
        [(cx - cinch_half - 6, rope_y + 4), (cx + cinch_half + 6, rope_y + 4)],
        fill=ROPE_DARK, width=3 * SUPERSAMPLE,
    )
    # Knot
    d.ellipse(
        [cx - 14, rope_y - 14, cx + 14, rope_y + 14],
        fill=ROPE, outline=OUTLINE, width=4 * SUPERSAMPLE,
    )
    # Loose rope ends hanging down
    for sign in (-1, 1):
        d.line(
            [(cx + sign * 8, rope_y + 2),
             (cx + sign * 22, rope_y + int(H * 0.04)),
             (cx + sign * 18, rope_y + int(H * 0.08))],
            fill=ROPE, width=6 * SUPERSAMPLE, joint="curve",
        )


def draw_gems(img):
    d = ImageDraw.Draw(img, "RGBA")
    cx = W // 2
    # Place 5 gems poking up out of the lip. Y values are above the lip line.
    base_y = int(H * 0.28)
    positions = [
        (cx - int(W * 0.18), base_y - int(H * 0.02), 1.0,  -0.15),
        (cx - int(W * 0.07), base_y - int(H * 0.10), 1.15,  0.05),
        (cx + int(W * 0.04), base_y - int(H * 0.14), 1.25, -0.05),
        (cx + int(W * 0.15), base_y - int(H * 0.09), 1.10,  0.10),
        (cx + int(W * 0.23), base_y - int(H * 0.02), 0.95, -0.10),
    ]
    base_r = int(W * 0.07)

    for (gx, gy, scale, tilt), (bright, dark) in zip(positions, GEM_COLORS):
        r = int(base_r * scale)
        # Gem shape: faceted hexagon-ish (top point, two upper shoulders,
        # two lower shoulders, bottom point).
        from math import sin, cos
        pts_local = [
            ( 0.00, -1.00),
            ( 0.78, -0.35),
            ( 0.55,  0.85),
            (-0.55,  0.85),
            (-0.78, -0.35),
        ]
        pts = []
        for px, py in pts_local:
            x = px * r * cos(tilt) - py * r * sin(tilt)
            y = px * r * sin(tilt) + py * r * cos(tilt)
            pts.append((gx + x, gy + y))
        d.polygon(pts, fill=bright + (255,))

        # Inner dark facet on the lower-right for depth.
        inner_local = [
            (0.0, -1.00),
            (0.78, -0.35),
            (0.55, 0.85),
            (0.0, 0.85),
            (0.0, -0.20),
        ]
        ipts = []
        for px, py in inner_local:
            x = px * r * cos(tilt) - py * r * sin(tilt)
            y = px * r * sin(tilt) + py * r * cos(tilt)
            ipts.append((gx + x, gy + y))
        d.polygon(ipts, fill=dark + (255,))

        # Outline
        outline(d, pts, color=OUTLINE, width=5 * SUPERSAMPLE)

        # Bright highlight streak on upper-left facet.
        hl_local = [
            (-0.05, -0.85),
            (0.30, -0.70),
            (0.20, -0.30),
            (-0.20, -0.40),
        ]
        hpts = []
        for px, py in hl_local:
            x = px * r * cos(tilt) - py * r * sin(tilt)
            y = px * r * sin(tilt) + py * r * cos(tilt)
            hpts.append((gx + x, gy + y))
        d.polygon(hpts, fill=(255, 255, 255, 200))


def build():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_sack(img)
    draw_gems(img)

    img = img.resize((CELL_W, CELL_H), Image.LANCZOS)

    BUILD_SPRITES.mkdir(parents=True, exist_ok=True)
    BUILD_ASSETS.mkdir(parents=True, exist_ok=True)
    png_path = BUILD_SPRITES / "GemBag.png"
    webp_path = BUILD_ASSETS / "GemBag.webp"
    img.save(png_path, "PNG", optimize=True)
    img.save(webp_path, quality=92, method=6)
    return png_path, webp_path


if __name__ == "__main__":
    p, w = build()
    print(f"wrote {p} ({p.stat().st_size/1024:.1f} KB)")
    print(f"wrote {w} ({w.stat().st_size/1024:.1f} KB)")
