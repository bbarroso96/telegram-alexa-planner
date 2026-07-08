"""Standalone status icons for the reTerminal — a fillable battery and a
thermometer — rendered as transparent monochrome PNGs. Served by the web app so
SenseCraft HMI image widgets can point at a URL (e.g. /battery.png?level=80)
instead of re-uploading files. Solid black on transparent, supersampled then
downsampled so the strokes stay smooth on the e-paper panel.
"""
import io

from PIL import Image, ImageDraw

S = 4  # supersample factor
BLACK = (0, 0, 0, 255)


def _finish(img: Image.Image, w: int, h: int) -> bytes:
    img = img.resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def battery(level: int = 80) -> bytes:
    """Vertical battery filled to `level` percent (0-100) from the bottom."""
    level = max(0, min(100, int(level)))
    W, H = 96, 172
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = W // 2
    # terminal nub on top
    dr.rounded_rectangle([(cx - 20) * S, 6 * S, (cx + 20) * S, 24 * S], radius=6 * S, fill=BLACK)
    # body outline
    dr.rounded_rectangle([12 * S, 24 * S, (W - 12) * S, (H - 8) * S], radius=14 * S,
                         outline=BLACK, width=7 * S)
    # fill from the bottom, inset from the outline
    if level > 0:
        top_full, bottom = 36, 152
        fill_top = bottom - level / 100 * (bottom - top_full)
        dr.rounded_rectangle([24 * S, fill_top * S, (W - 24) * S, bottom * S],
                             radius=7 * S, fill=BLACK)
    return _finish(img, W, H)


def thermometer() -> bytes:
    """Thermometer glyph (no reading — the value goes beside it in SenseCraft)."""
    W, H = 84, 168
    img = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx = 42
    dr.ellipse([(cx - 26) * S, 112 * S, (cx + 26) * S, 164 * S], fill=BLACK)          # bulb
    dr.rounded_rectangle([(cx - 15) * S, 14 * S, (cx + 15) * S, 138 * S], radius=15 * S,
                         outline=BLACK, width=7 * S)                                   # tube
    dr.rounded_rectangle([(cx - 7) * S, 74 * S, (cx + 7) * S, 140 * S], radius=7 * S,
                         fill=BLACK)                                                   # mercury
    for ty in (40, 64, 88):                                                           # ticks
        dr.line([(cx + 18) * S, ty * S, (cx + 30) * S, ty * S], fill=BLACK, width=5 * S)
    return _finish(img, W, H)
