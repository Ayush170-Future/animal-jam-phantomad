#!/usr/bin/env python3
"""Inline all assets/* references in playable.html as base64 data URIs."""
import base64
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "playable.html"
DST = ROOT.parent / "dist" / "playable.html"
ASSETS = ROOT / "assets"

MIME = {
    ".webp": "image/webp",
    ".png":  "image/png",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".mp3":  "audio/mpeg",
    ".wav":  "audio/wav",
    ".ogg":  "audio/ogg",
}

def data_uri(path: Path) -> str:
    mime = MIME[path.suffix.lower()]
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"

def main():
    html = SRC.read_text()
    # Match 'assets/<file>' (single quoted)
    pattern = re.compile(r"'assets/([^']+)'")
    matches = sorted(set(pattern.findall(html)))
    print(f"Inlining {len(matches)} assets:")
    sizes = []
    for name in matches:
        p = ASSETS / name
        if not p.exists():
            print(f"  ! MISSING: {name}")
            continue
        sz = p.stat().st_size
        sizes.append((name, sz))
        uri = data_uri(p)
        html = html.replace(f"'assets/{name}'", f"'{uri}'")
        print(f"  + {name}  ({sz/1024:.1f} KB raw -> {len(uri)/1024:.1f} KB b64)")
    DST.parent.mkdir(parents=True, exist_ok=True)
    DST.write_text(html)
    out_kb = DST.stat().st_size / 1024
    raw_kb = sum(s for _, s in sizes) / 1024
    print(f"\nRaw assets: {raw_kb:.1f} KB")
    print(f"Final HTML: {out_kb:.1f} KB  ->  {DST}")

if __name__ == "__main__":
    main()
