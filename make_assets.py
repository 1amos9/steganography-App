"""
Make original logo and icon assets for the Stego Suite.
Run once: python make_assets.py
Creates an assets folder with logo.png and a set of icon_*.png files.
The art is original, drawn with simple shapes. Not copied from QuickCrypto.
"""

import os
import math
from PIL import Image, ImageDraw

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
os.makedirs(ASSETS, exist_ok=True)

YELLOW = (242, 194, 0, 255)
YELLOW_DARK = (184, 138, 0, 255)
BLACK = (10, 10, 10, 255)
WHITE = (250, 250, 240, 255)
GREY_HI = (210, 210, 210, 255)
GREY_LO = (70, 70, 70, 255)
TILE = (28, 28, 28, 255)


def new_canvas(size=40):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def tile_bg(d, size, color=TILE):
    d.rounded_rectangle([1, 1, size - 2, size - 2], radius=7, fill=color,
                        outline=YELLOW_DARK, width=1)


def save(img, name):
    img.save(os.path.join(ASSETS, name))


# ---------------- logo: a metallic sphere with a yellow core ----------------
def make_logo(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # outer sphere, light to dark for a metal look
    steps = size // 2
    cx = cy = size / 2
    for r in range(steps, 0, -1):
        t = r / steps
        shade = int(60 + (1 - t) * 150)
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=(shade, shade, shade, 255))
    # yellow core glow
    core = size * 0.22
    d.ellipse([cx - core, cy - core, cx + core, cy + core], fill=YELLOW)
    d.ellipse([cx - core * 0.5, cy - core * 0.7, cx + core * 0.1, cy - core * 0.1],
              fill=WHITE)
    # rim highlight
    d.arc([3, 3, size - 4, size - 4], start=200, end=320, fill=GREY_HI, width=2)
    save(img, "logo.png")


# ---------------- icon helpers ----------------
def icon_lock(size=40, open_shackle=False):
    img, d = new_canvas(size)
    tile_bg(d, size)
    body = [12, 20, 28, 33]
    d.rounded_rectangle(body, radius=2, fill=YELLOW)
    if open_shackle:
        d.arc([13, 8, 24, 22], start=160, end=20, fill=WHITE, width=3)
    else:
        d.arc([14, 9, 26, 24], start=180, end=360, fill=WHITE, width=3)
    d.ellipse([19, 24, 21, 27], fill=BLACK)
    return img


def icon_file(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.polygon([(14, 9), (24, 9), (30, 15), (30, 31), (14, 31)], fill=WHITE)
    d.polygon([(24, 9), (24, 15), (30, 15)], fill=GREY_HI)
    for y in (18, 22, 26):
        d.line([17, y, 27, y], fill=GREY_LO, width=1)
    return img


def icon_folder(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.polygon([(10, 16), (17, 16), (20, 13), (30, 13), (30, 16)], fill=YELLOW_DARK)
    d.rounded_rectangle([10, 16, 30, 30], radius=2, fill=YELLOW)
    return img


def icon_copy(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.rounded_rectangle([12, 12, 24, 26], radius=2, fill=GREY_HI)
    d.rounded_rectangle([16, 16, 28, 30], radius=2, fill=WHITE, outline=GREY_LO)
    return img


def icon_paste(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.rounded_rectangle([13, 13, 27, 30], radius=2, fill=WHITE)
    d.rounded_rectangle([16, 10, 24, 15], radius=2, fill=YELLOW)
    return img


def icon_clear(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.line([14, 14, 26, 26], fill=YELLOW, width=3)
    d.line([26, 14, 14, 26], fill=YELLOW, width=3)
    return img


def icon_flame(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.polygon([(20, 9), (26, 20), (24, 28), (16, 28), (14, 20)], fill=(255, 120, 0, 255))
    d.polygon([(20, 16), (23, 23), (20, 28), (17, 23)], fill=YELLOW)
    return img


def icon_shield(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.polygon([(20, 9), (29, 13), (29, 22), (20, 31), (11, 22), (11, 13)], fill=YELLOW)
    d.line([20, 14, 20, 26], fill=BLACK, width=2)
    d.line([14, 20, 26, 20], fill=BLACK, width=2)
    return img


def icon_eye(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.ellipse([11, 15, 29, 25], fill=WHITE)
    d.ellipse([17, 16, 23, 24], fill=YELLOW_DARK)
    d.ellipse([19, 18, 21, 22], fill=BLACK)
    return img


def icon_key(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.ellipse([11, 14, 21, 24], outline=YELLOW, width=3)
    d.line([20, 19, 30, 19], fill=YELLOW, width=3)
    d.line([27, 19, 27, 24], fill=YELLOW, width=3)
    d.line([30, 19, 30, 23], fill=YELLOW, width=3)
    return img


def icon_gear(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    cx = cy = 20
    for a in range(0, 360, 45):
        rad = math.radians(a)
        x = cx + math.cos(rad) * 11
        y = cy + math.sin(rad) * 11
        d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=YELLOW)
    d.ellipse([13, 13, 27, 27], fill=YELLOW)
    d.ellipse([17, 17, 23, 23], fill=TILE)
    return img


def icon_image(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.rounded_rectangle([10, 12, 30, 28], radius=2, fill=WHITE, outline=GREY_LO)
    d.ellipse([14, 15, 18, 19], fill=YELLOW)
    d.polygon([(13, 27), (20, 19), (27, 27)], fill=YELLOW_DARK)
    return img


def icon_save(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.rounded_rectangle([11, 11, 29, 29], radius=2, fill=YELLOW)
    d.rectangle([15, 11, 25, 17], fill=TILE)
    d.rectangle([21, 12, 24, 16], fill=YELLOW)
    d.rounded_rectangle([15, 21, 25, 28], radius=1, fill=WHITE)
    return img


def icon_open(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.polygon([(10, 17), (16, 17), (19, 14), (30, 14), (30, 18)], fill=YELLOW_DARK)
    d.polygon([(10, 18), (30, 18), (27, 30), (10, 30)], fill=YELLOW)
    return img


def icon_password(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    for i, x in enumerate((13, 20, 27)):
        d.ellipse([x - 3, 18, x + 3, 24], fill=YELLOW if i != 1 else WHITE)
    return img


def icon_mail(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.rounded_rectangle([10, 14, 30, 27], radius=2, fill=WHITE, outline=GREY_LO)
    d.line([10, 15, 20, 22], fill=YELLOW_DARK, width=2)
    d.line([30, 15, 20, 22], fill=YELLOW_DARK, width=2)
    return img


def icon_info(size=40):
    img, d = new_canvas(size)
    tile_bg(d, size)
    d.ellipse([12, 12, 28, 28], fill=YELLOW)
    d.ellipse([19, 15, 21, 17], fill=BLACK)
    d.rectangle([19, 19, 21, 25], fill=BLACK)
    return img


ICONS = {
    "lock": lambda: icon_lock(open_shackle=False),
    "unlock": lambda: icon_lock(open_shackle=True),
    "file": icon_file,
    "folder": icon_folder,
    "copy": icon_copy,
    "paste": icon_paste,
    "clear": icon_clear,
    "flame": icon_flame,
    "shield": icon_shield,
    "eye": icon_eye,
    "key": icon_key,
    "gear": icon_gear,
    "image": icon_image,
    "save": icon_save,
    "open": icon_open,
    "password": icon_password,
    "mail": icon_mail,
    "info": icon_info,
}


def build_all():
    make_logo()
    for name, fn in ICONS.items():
        save(fn(), f"icon_{name}.png")
    print(f"Assets written to {ASSETS}")
    print("Files:", len(os.listdir(ASSETS)))


if __name__ == "__main__":
    build_all()


def make_emblem():
    """Original circular seal for the startup splash. Not the QuickCrypto eagle."""
    import math
    size = 240
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = cy = size // 2

    # two outer rings
    d.ellipse([6, 6, size - 6, size - 6], outline=YELLOW, width=3)
    d.ellipse([16, 16, size - 16, size - 16], outline=YELLOW_DARK, width=2)

    # ring of small stars between the rings
    star_r = (size // 2) - 11
    for k in range(24):
        a = (k / 24) * 2 * math.pi
        sx = cx + star_r * math.cos(a)
        sy = cy + star_r * math.sin(a)
        d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=YELLOW)

    # central shield
    sw, sh = 70, 86
    left = cx - sw // 2
    top = cy - sh // 2 - 4
    d.polygon([
        (cx, top),
        (left + sw, top + 14),
        (left + sw, top + sh - 26),
        (cx, top + sh),
        (left, top + sh - 26),
        (left, top + 14),
    ], outline=YELLOW, width=3)

    # keyhole inside the shield
    d.ellipse([cx - 9, cy - 14, cx + 9, cy + 4], outline=YELLOW, width=3)
    d.polygon([(cx - 4, cy), (cx + 4, cy), (cx + 7, cy + 24), (cx - 7, cy + 24)],
              fill=YELLOW)

    img.save(os.path.join(ASSETS, "emblem.png"))


make_emblem()
print("emblem.png written")
