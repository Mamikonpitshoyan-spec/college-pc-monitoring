"""Generate admin app icon variants (cyber-blue theme) as PNG + ICO.

Run: python gen_icons.py  →  ../branding/icon-1.png ... icon-5.png (+ .ico)
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT_DIR = Path(__file__).resolve().parent
SIZE = 512
BG = (12, 21, 49, 255)        # #0c1531 — как панель дашборда
BG_DARK = (7, 12, 28, 255)    # #070c1c — фон страницы
BORDER = (24, 38, 85, 255)    # #182655
TEAL = (46, 230, 214, 255)    # #2ee6d6 — акцент
VIOLET = (139, 124, 246, 255) # #8b7cf6
GREEN = (46, 230, 138, 255)
WHITE = (220, 228, 245, 255)

ROUND_RADIUS = 110


def base_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=ROUND_RADIUS, fill=BG, outline=BORDER, width=6)
    return image, draw


def save(image: Image.Image, name: str) -> None:
    png = OUT_DIR / f"{name}.png"
    image.save(png)
    ico = OUT_DIR / f"{name}.ico"
    image.save(ico, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    print(f"saved {png.name} + {ico.name}")


# ---------- 1. Пульс (как логотип дашборда) ----------
def icon_pulse() -> None:
    image, draw = base_canvas()
    points = [
        (70, 256), (170, 256), (215, 150), (280, 360), (330, 256), (442, 256),
    ]
    draw.line(points, fill=TEAL, width=34, joint="curve")
    for point in (points[0], points[-1]):
        draw.ellipse((point[0] - 17, point[1] - 17, point[0] + 17, point[1] + 17), fill=TEAL)
    draw.ellipse((253, 333, 307, 387), fill=VIOLET)  # точка-акцент
    save(image, "icon-1-pulse")


# ---------- 2. Монитор с пульсом ----------
def icon_monitor() -> None:
    image, draw = base_canvas()
    draw.rounded_rectangle((90, 110, 422, 330), radius=36, outline=TEAL, width=22)
    points = [(140, 240), (210, 240), (245, 175), (295, 285), (330, 240), (372, 240)]
    draw.line(points, fill=TEAL, width=18, joint="curve")
    draw.line((256, 330, 256, 380), fill=TEAL, width=22)
    draw.line((180, 392, 332, 392), fill=TEAL, width=22)
    draw.ellipse((410, 82, 446, 118), fill=GREEN)  # статус-точка
    save(image, "icon-2-monitor")


# ---------- 3. Щит с пульсом ----------
def icon_shield() -> None:
    image, draw = base_canvas()
    shield = [(256, 70), (400, 130), (400, 270), (256, 442), (112, 270), (112, 130), (256, 70)]
    draw.line(shield + [shield[0]], fill=TEAL, width=26, joint="curve")
    points = [(170, 260), (225, 260), (255, 200), (305, 310), (340, 260), (342, 260)]
    draw.line(points, fill=TEAL, width=20, joint="curve")
    draw.ellipse((238, 350, 274, 386), fill=VIOLET)
    save(image, "icon-3-shield")


# ---------- 4. Сеть: админ в центре ----------
def icon_network() -> None:
    image, draw = base_canvas()
    center = (256, 256)
    nodes = [(256, 105), (385, 180), (385, 330), (256, 407), (127, 330), (127, 180)]
    for node in nodes:
        draw.line((center, node), fill=BORDER, width=16)
    for node in nodes:
        draw.ellipse((node[0] - 34, node[1] - 34, node[0] + 34, node[1] + 34), fill=TEAL)
    draw.ellipse((center[0] - 62, center[1] - 62, center[0] + 62, center[1] + 62), fill=BG, outline=VIOLET, width=10)
    draw.ellipse((center[0] - 40, center[1] - 40, center[0] + 40, center[1] + 40), fill=VIOLET)
    save(image, "icon-4-network")


# ---------- 5. Спидометр ----------
def icon_gauge() -> None:
    image, draw = base_canvas()
    draw.arc((100, 120, 412, 412), start=180, end=360, fill=TEAL, width=30)
    for angle, color in ((200, TEAL), (270, VIOLET), (340, GREEN)):
        import math
        rad = math.radians(angle)
        outer = (256 + 175 * math.cos(rad), 266 + 175 * math.sin(rad))
        inner = (256 + 120 * math.cos(rad), 266 + 120 * math.sin(rad))
        draw.line((inner, outer), fill=color, width=16)
    draw.line((256, 266, 350, 190), fill=WHITE, width=18)
    draw.ellipse((230, 240, 282, 292), fill=TEAL)
    save(image, "icon-5-gauge")


# ---------- 6. Иконка юзера: монитор в зелёной гамме ----------
def icon_user() -> None:
    image, draw = base_canvas()
    green = (46, 230, 138, 255)
    draw.rounded_rectangle((90, 110, 422, 330), radius=36, outline=green, width=22)
    points = [(140, 240), (210, 240), (245, 175), (295, 285), (330, 240), (372, 240)]
    draw.line(points, fill=green, width=18, joint="curve")
    draw.line((256, 330, 256, 380), fill=green, width=22)
    draw.line((180, 392, 332, 392), fill=green, width=22)
    draw.ellipse((410, 82, 446, 118), fill=TEAL)  # точка связи
    save(image, "icon-user")


if __name__ == "__main__":
    icon_user()
    icon_pulse()
    icon_monitor()
    icon_shield()
    icon_network()
    icon_gauge()
    print("all icons generated")
