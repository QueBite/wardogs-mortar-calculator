"""Generate a multi-resolution .ico for the Mortar Calculator exe."""
from PIL import Image, ImageDraw
import math

S = 512                      # draw large, downsample for crisp small sizes
img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

OLIVE = (58, 74, 46, 255)    # military olive drab background
EDGE = (30, 40, 24, 255)
GREEN = (126, 214, 94, 255)  # phosphor green, matches the app's #0a0 text
PALE = (228, 238, 214, 255)

# rounded-square body
d.rounded_rectangle([8, 8, S - 8, S - 8], radius=96, fill=OLIVE,
                    outline=EDGE, width=10)

# ballistic trajectory arc: launch bottom-left, impact bottom-right
pts = []
x0, x1 = 96, 416
apex = 128
for i in range(121):
    t = i / 120
    x = x0 + (x1 - x0) * t
    y = 408 - (408 - apex) * (4 * t * (1 - t))   # parabola
    pts.append((x, y))
d.line(pts, fill=GREEN, width=18, joint="curve")

# launch marker (mortar tube) at the start of the arc
d.line([(72, 424), (140, 320)], fill=PALE, width=26)
d.ellipse([60, 412, 108, 460], fill=PALE)

# crosshair reticle over the impact point
cx, cy, r = 416, 408, 62
d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=PALE, width=14)
for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
    d.line([(cx + dx * (r - 30), cy + dy * (r - 30)),
            (cx + dx * (r + 26), cy + dy * (r + 26))], fill=PALE, width=14)

sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save("mortar.ico", format="ICO", sizes=sizes)
print("mortar.ico written with sizes:", sizes)
