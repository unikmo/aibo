"""Generate deterministic AIBO desktop icons from the Control Centre monogram.

No brand-font dependencies. Icons are bundled only in the local Windows/macOS apps.
"""
from pathlib import Path
from PIL import Image, ImageDraw

OUTPUT = Path(__file__).resolve().parent / "icons"
OUTPUT.mkdir(parents=True, exist_ok=True)
N = 1024
image = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(image)
# Graphite rounded tile, narrow premium gold A without extra decorative layers.
d.rounded_rectangle((20, 20, 1004, 1004), radius=230, fill="#242927")
gold = "#D5BC8A"
# Draw symmetrical A as strokes with restrained geometry.
d.line([(310, 746), (506, 269), (704, 746)], fill=gold, width=79, joint="curve")
d.line([(399, 591), (616, 591)], fill=gold, width=69)
d.rounded_rectangle((420, 748, 601, 764), radius=8, fill="#242927")
image.save(OUTPUT / "AIBO.ico", format="ICO", sizes=[
    (16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
    (128, 128), (256, 256)
])
image.save(OUTPUT / "AIBO.icns", format="ICNS")
print("Created desktop icons:", OUTPUT / "AIBO.ico", OUTPUT / "AIBO.icns")
