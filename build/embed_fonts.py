"""Subset Animal Jam fonts to printable ASCII (covers everything the game
draws), convert to WOFF2, and inject @font-face data: URIs into playable.html.

We use:
  - Tiki-Island   for big titles / hero text
  - CCDigitalDelivery-Bold  for everything else (UI, score, labels, buttons)
"""
import base64
import re
from pathlib import Path
from io import BytesIO
from fontTools.ttLib import TTFont
from fontTools.subset import Subsetter

ROOT = Path("/Users/ayushsingh/Documents/programming/animal-jam-ad")
FONTS = ROOT / "Falling Phantoms" / "Fonts"
PLAYABLE = ROOT / "build" / "playable.html"

# (family-name-used-in-CSS, source-path)
FONT_MAP = [
    ("AJTiki",
     FONTS / "Tiki - Used for Titles" / "Tiki-Island.otf"),
    ("AJDelivery",
     FONTS / "CC_Digital_Delivery" / "Comicraft - CCDigitalDelivery-Bold.otf"),
]
# Glyph coverage: printable ASCII plus common punctuation.
SUBSET_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " .,!?:;'\"-+/&%@#*()[]{}<>=\\|^~`$"
)


def subset_to_woff2(src: Path) -> bytes:
    font = TTFont(str(src))
    sub = Subsetter()
    sub.populate(text=SUBSET_CHARS)
    sub.subset(font)
    font.flavor = "woff2"
    buf = BytesIO()
    font.save(buf)
    return buf.getvalue()


def main():
    css_blocks = []
    print("Subsetting fonts:")
    for family, src in FONT_MAP:
        woff2 = subset_to_woff2(src)
        b64 = base64.b64encode(woff2).decode("ascii")
        raw_kb = src.stat().st_size / 1024
        new_kb = len(woff2) / 1024
        print(f"  {family:14s}  {raw_kb:6.1f} KB OTF -> {new_kb:5.1f} KB WOFF2 subset")
        css_blocks.append(
            f"@font-face {{ font-family: '{family}'; "
            f"font-display: block; "
            f"src: url(data:font/woff2;base64,{b64}) format('woff2'); }}"
        )

    block = "\n  ".join(css_blocks)
    marker_start = "/* AJ_FONTS_START */"
    marker_end = "/* AJ_FONTS_END */"
    new_section = (
        f"{marker_start}\n  {block}\n  {marker_end}"
    )

    html = PLAYABLE.read_text()
    if marker_start in html:
        html = re.sub(
            re.escape(marker_start) + r".*?" + re.escape(marker_end),
            new_section,
            html,
            flags=re.DOTALL,
        )
    else:
        # Insert just before the first existing rule in <style>.
        html = html.replace(
            "<style>\n",
            f"<style>\n  {new_section}\n",
            1,
        )
    PLAYABLE.write_text(html)
    print(f"\nwrote @font-face block into {PLAYABLE.name}")


if __name__ == "__main__":
    main()
