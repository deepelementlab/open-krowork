"""Generate unique .ico icons for KroWork apps using Pillow."""

import hashlib
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# Distinct color palette - each app gets a unique color based on its name
PALETTE = [
    (0, 212, 255),     # #00D4FF - Cyan
    (255, 71, 87),     # #FF4757 - Red
    (46, 213, 115),    # #2ED573 - Green
    (255, 165, 2),     # #FFA502 - Orange
    (155, 89, 255),    # #9B59FF - Purple
    (255, 107, 181),   # #FF6BB5 - Pink
    (0, 184, 217),     # #00B8D9 - Teal
    (241, 196, 15),    # #F1C40F - Yellow
    (52, 152, 219),    # #3498DB - Blue
    (230, 126, 34),    # #E67E22 - Dark Orange
    (26, 188, 156),    # #1ABC9C - Mint
    (231, 76, 60),     # #E74C3C - Crimson
    (142, 68, 173),    # #8E44AD - Violet
    (39, 174, 96),     # #27AE60 - Emerald
    (211, 84, 0),      # #D35400 - Rust
    (22, 160, 133),    # #16A085 - Sea Green
    (192, 57, 43),     # #C0392B - Dark Red
    (41, 128, 185),    # #2980B9 - Steel Blue
    (243, 156, 18),    # #F39C12 - Amber
    (127, 140, 141),   # #7F8C8D - Gray
]


def _color_for_name(name: str) -> tuple:
    """Pick a deterministic color for an app name."""
    h = int(hashlib.md5(name.lower().encode()).hexdigest(), 16)
    return PALETTE[h % len(PALETTE)]


def _get_font(size: int) -> ImageFont.FreeTypeFont:
    """Get a suitable font, trying several common paths."""
    # Try common font paths on Windows
    font_paths = [
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/seguisym.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    # Fallback to default
    return ImageFont.load_default()


def _abbreviate(name: str) -> str:
    """Create a 1-2 letter abbreviation from an app name.

    Examples:
        'todo-manager' -> 'TM'
        'api-tester' -> 'AT'
        'markdown-notebook' -> 'MN'
        'password-generator' -> 'PG'
        'my-awesome-app' -> 'MA'
    """
    parts = name.replace("_", "-").split("-")
    # Filter out generic words
    skip = {"app", "the", "a", "an", "my", "for", "of", "and", "with", "tool", "manager", "generator"}
    meaningful = [p for p in parts if p.lower() not in skip and len(p) > 0]
    if not meaningful:
        meaningful = parts

    if len(meaningful) >= 2:
        return (meaningful[0][0] + meaningful[1][0]).upper()
    elif len(meaningful) == 1:
        word = meaningful[0]
        if len(word) >= 2:
            return word[:2].upper()
        return word.upper()
    return name[:2].upper()


def generate_icon(app_name: str, output_path: str, size: int = 64) -> str:
    """Generate a unique .ico file for an app.

    Args:
        app_name: The app identifier (e.g. 'todo-manager')
        output_path: Where to save the .ico file
        size: Icon size in pixels (default 64)

    Returns:
        Path to the generated .ico file.
    """
    color = _color_for_name(app_name)
    abbr = _abbreviate(app_name)

    # Create image
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Draw rounded-rectangle background
    radius = size // 4
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)],
        radius=radius,
        fill=color,
    )

    # Draw a subtle gradient overlay (lighter at top)
    for y in range(size // 2):
        alpha = int(40 * (1 - y / (size // 2)))
        draw.line([(0, y), (size - 1, y)], fill=(255, 255, 255, alpha))

    # Draw abbreviation text
    font_size = size // 2 if len(abbr) <= 2 else size // 3
    font = _get_font(font_size)

    # Center text
    bbox = draw.textbbox((0, 0), abbr, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = (size - tw) // 2
    y = (size - th) // 2 - bbox[1]

    # Text shadow
    draw.text((x + 1, y + 1), abbr, fill=(0, 0, 0, 80), font=font)
    # Text
    draw.text((x, y), abbr, fill=(255, 255, 255, 240), font=font)

    # Save as .ico (with multiple sizes for best display)
    icon_sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = []
    for s in icon_sizes:
        resized = img.resize((s, s), Image.LANCZOS)
        icons.append(resized)

    # Save the largest as the base, with all sizes embedded
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    # Save with multiple sizes
    icons[0].save(
        str(output),
        format="ICO",
        sizes=[(s, s) for s in icon_sizes],
        append_images=icons[1:],
    )

    return str(output)


def generate_icon_for_app(app_dir: Path, app_name: str) -> str:
    """Generate an icon for a KroWork app and save it in the app directory.

    Returns the path to the generated .ico file.
    """
    icon_path = app_dir / "icon.ico"
    generate_icon(app_name, str(icon_path))
    return str(icon_path)
