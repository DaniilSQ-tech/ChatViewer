"""Генерация иконки приложения ChatViewer — логотип CV."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Современная палитра: indigo-градиент + белый текст
BG_TOP = (99, 102, 241)       # indigo-500
BG_BOTTOM = (67, 56, 202)     # indigo-700
TEXT_COLOR = (255, 255, 255)
SHADOW_COLOR = (49, 46, 129)  # indigo-900

FONT_CANDIDATES = (
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\calibrib.ttf"),
)


def _gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    img = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(img)
    for y in range(size):
        ratio = y / max(size - 1, 1)
        color = tuple(
            int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3)
        )
        draw.line([(0, y), (size, y)], fill=color)
    return img


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def draw_icon(size: int) -> Image.Image:
    """Рисует современный логотип CV на скруглённом градиентном фоне."""
    radius = max(size // 5, 2)
    gradient = _gradient(size, BG_TOP, BG_BOTTOM)

    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, size - 1, size - 1),
        radius=radius,
        fill=255,
    )

    img = Image.new("RGB", (size, size), BG_BOTTOM)
    img.paste(gradient, mask=mask)

    draw = ImageDraw.Draw(img)
    font_size = max(int(size * 0.44), 7 if size >= 16 else 6)
    font = _load_font(font_size)
    text = "CV"

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (size - text_w) // 2 - bbox[0]
    y = (size - text_h) // 2 - bbox[1]

    if size >= 32:
        offset = max(1, size // 64)
        draw.text((x + offset, y + offset), text, font=font, fill=SHADOW_COLOR)
    draw.text((x, y), text, font=font, fill=TEXT_COLOR)

    # Акцентная линия под буквами (только на средних и больших размерах)
    if size >= 48:
        line_w = int(size * 0.36)
        line_h = max(2, size // 32)
        line_x = (size - line_w) // 2
        line_y = y + text_h + max(1, size // 32)
        draw.rounded_rectangle(
            (line_x, line_y, line_x + line_w, line_y + line_h),
            radius=line_h // 2,
            fill=(165, 180, 252),
        )

    return img


sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = [draw_icon(s) for s, _ in sizes]

rgb_icons: list[Image.Image] = []
for icon in icons:
    rgb_icons.append(icon.convert("RGB") if icon.mode != "RGB" else icon)

try:
    rgb_icons[0].save(
        "app.ico",
        format="ICO",
        sizes=sizes,
        append_images=rgb_icons[1:],
    )
    print("Иконка 'app.ico' создана!")
    print("   Дизайн: логотип CV на indigo-градиенте")
    print("   Стиль: скруглённые углы, белые буквы, акцентная линия")
except Exception as e:
    print(f"Ошибка при сохранении: {e}")
    print("Попытка альтернативного метода сохранения...")
    rgb_icons[0].save("app.ico", format="ICO")
    print("Иконка 'app.ico' создана (только один размер)")
