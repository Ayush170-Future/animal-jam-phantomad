"""Build a 1280x720 high-res background.

The high-res Background.png has a transparent sky and binary (0/255) alpha,
so we composite it over a hand-painted sky gradient. We used to use an
upscaled Dark.png as the base, but its blurry tree silhouettes from LANCZOS
upscale showed up as halos around the (sharper, slightly-different-shape)
hi-res trees. A pure gradient base has nothing tree-shaped to leak through.
"""
from pathlib import Path
from PIL import Image, ImageEnhance

ROOT = Path("/Users/ayushsingh/Documents/programming/animal-jam-ad")
HI_SRC   = ROOT / "Falling Phantoms/UI + 2D Assets/Background.png"
OUT_PNG  = ROOT / "build/sprites/Background.png"
OUT_WEBP = ROOT / "build/assets/Background.webp"

VW, VH = 1280, 720

# Sky gradient stops chosen to match the Dark variant's sunset tones.
# Anchored at y positions matching the high-res image proportions.
SKY_STOPS = [
    (0,        (60, 24, 8)),     # top of sky — deep red-brown
    (80,       (145, 56, 8)),    # upper sky
    (170,      (200, 88, 24)),   # mid sky (where the mountain peeks through)
    (250,      (130, 60, 26)),   # near horizon haze
    (VH,       (60, 32, 18)),    # below trees (covered, but smooth gradient)
]


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def build_sky():
    sky = Image.new("RGB", (VW, VH))
    px = sky.load()
    # Pre-compute color for each row by interpolating between stops.
    row_colors = [None] * VH
    for i in range(len(SKY_STOPS) - 1):
        y0, c0 = SKY_STOPS[i]
        y1, c1 = SKY_STOPS[i + 1]
        for y in range(y0, min(y1, VH)):
            t = (y - y0) / (y1 - y0) if y1 > y0 else 0
            row_colors[y] = lerp(c0, c1, t)
    for y in range(VH):
        c = row_colors[y]
        for x in range(VW):
            px[x, y] = c
    return sky


hi = Image.open(HI_SRC).convert("RGBA")
print(f"hi-res FG: {hi.size}")

sky = build_sky().convert("RGBA")

# Darken the foreground to match the moody/dark aesthetic.
fg_rgb = hi.convert("RGB")
fg_rgb = ImageEnhance.Brightness(fg_rgb).enhance(0.62)
fg_rgb = ImageEnhance.Color(fg_rgb).enhance(0.85)
fg_darkened = Image.merge("RGBA", (*fg_rgb.split(), hi.split()[-1]))

out = Image.alpha_composite(sky, fg_darkened).convert("RGB")
out.save(OUT_PNG, "PNG", optimize=True)
out.save(OUT_WEBP, "WEBP", quality=88, method=6)

print(f"wrote {OUT_PNG} ({OUT_PNG.stat().st_size/1024:.1f} KB)")
print(f"wrote {OUT_WEBP} ({OUT_WEBP.stat().st_size/1024:.1f} KB)")
