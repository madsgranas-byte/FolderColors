"""Draws the folder icons and writes them as .ico files.

Pure Python, no Pillow: every shape is a rounded rectangle described by a
signed distance function, which also gives smooth anti-aliased edges.
"""

import math
import struct
import sys
import zlib
from pathlib import Path

from palette import COLORS, hex_to_rgb

ICO_SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 256)

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
PAPER = (239, 241, 245)  # Catppuccin Latte "base"


def mix(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def rounded_rect(px, py, x0, y0, x1, y1, r):
    """Signed distance from (px, py) to a rounded rectangle. Negative inside."""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    qx = abs(px - cx) - ((x1 - x0) / 2 - r)
    qy = abs(py - cy) - ((y1 - y0) / 2 - r)
    outside = math.hypot(max(qx, 0.0), max(qy, 0.0))
    inside = min(max(qx, qy), 0.0)
    return outside + inside - r


def coverage(distance, size, softness=1.0):
    """How much of the pixel is inside the shape (0..1)."""
    return min(1.0, max(0.0, 0.5 - distance * size / softness))


def over(dst, color, alpha):
    """Composite a straight-alpha color over a premultiplied RGBA pixel."""
    if alpha <= 0:
        return dst
    r, g, b, a = dst
    k = 1 - alpha
    return (color[0] * alpha + r * k, color[1] * alpha + g * k,
            color[2] * alpha + b * k, alpha + a * k)


def render_folder(size, rgb):
    """Returns `size` rows of RGBA byte strings."""
    back = mix(rgb, BLACK, 0.28)
    front_top = mix(rgb, WHITE, 0.22)
    front_bottom = rgb
    highlight = mix(rgb, WHITE, 0.55)

    # Everything is laid out on a 0..1 square.
    left, right, bottom = 0.06, 0.94, 0.86
    front_top_y = 0.33
    radius = 0.075
    hairline = 1.2 / size
    shadow = size >= 32

    rows = []
    for y in range(size):
        py = (y + 0.5) / size
        row = bytearray()
        for x in range(size):
            px = (x + 0.5) / size
            pixel = (0.0, 0.0, 0.0, 0.0)

            if shadow:
                d = rounded_rect(px, py - 0.025, left + 0.01, 0.2, right - 0.01, bottom, radius)
                pixel = over(pixel, BLACK, 0.28 * coverage(d, size, softness=0.05 * size))

            body = rounded_rect(px, py, left, 0.2, right, bottom, radius)
            tab = rounded_rect(px, py, left, 0.13, 0.43, 0.32, 0.06)
            pixel = over(pixel, back, coverage(min(body, tab), size))

            paper = rounded_rect(px, py, 0.13, 0.24, 0.87, 0.6, 0.035)
            pixel = over(pixel, PAPER, 0.95 * coverage(paper, size))

            front = rounded_rect(px, py, left, front_top_y, right, bottom, radius)
            a = coverage(front, size)
            if a > 0:
                t = min(1.0, max(0.0, (py - front_top_y) / (bottom - front_top_y)))
                color = mix(front_top, front_bottom, t)
                if py - front_top_y < hairline * 1.5 and size >= 24:
                    color = mix(color, highlight, 0.6)
                pixel = over(pixel, color, a)

            r, g, b, alpha = pixel
            if alpha > 0:
                r, g, b = r / alpha, g / alpha, b / alpha
            row += bytes((round(r), round(g), round(b), round(alpha * 255)))
        rows.append(bytes(row))
    return rows


def png_bytes(rows):
    height, width = len(rows), len(rows[0]) // 4

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    raw = b"".join(b"\x00" + row for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def ico_bytes(images):
    """images: list of (size, png bytes). Windows reads PNG entries in .ico files."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = len(header) + 16 * len(images)
    entries, data = b"", b""
    for size, png in images:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        data += png
        offset += len(png)
    return header + entries + data


def build_icons(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, (_, color) in COLORS.items():
        rgb = hex_to_rgb(color)
        images = [(s, png_bytes(render_folder(s, rgb))) for s in ICO_SIZES]
        (out_dir / f"{name}.ico").write_bytes(ico_bytes(images))
        print(f"  {name}.ico")


def build_preview(path, size=128, gap=16):
    """One PNG with every color side by side, for the README."""
    icons = [render_folder(size, hex_to_rgb(c)) for _, c in COLORS.values()]
    width = gap + len(icons) * (size + gap)
    blank = b"\x00\x00\x00\x00"
    rows = [blank * width for _ in range(gap)]
    for y in range(size):
        row = blank * gap
        for icon in icons:
            row += icon[y] + blank * gap
        rows.append(row)
    rows += [blank * width for _ in range(gap)]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(png_bytes(rows))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "build/icons"
    build_icons(target)
