"""Render a monochrome 'today' board for the reTerminal E1001 e-paper display.

The Pi does the layout with Pillow; the e-paper device just fetches this PNG on a
timer and displays it. Two orientations (landscape 800x480 / portrait 480x800) and
two calendar styles (a compact month grid or a two-week strip), selected by query
params. Tasks are priority-ordered (Major first) and fit-to-height with a
"+ N more" footer so the screen never overflows.
"""
import io
from datetime import date, timedelta
import calendar as _cal

from PIL import Image, ImageDraw, ImageFont

# 1-bit e-paper: no true grays. Hierarchy comes from font size/weight and dashed
# rules, never tone — gray text would either dither to a faded dot pattern or break
# up under a hard threshold, so everything legible is solid BLACK.
BLACK, WHITE = 0, 255
MARGIN = 26

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_REG_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
    "C:/Windows/Fonts/arial.ttf",
]
_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _font(size: int, bold: bool = False):
    for path in (_BOLD_PATHS if bold else _REG_PATHS):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def short_date(d: date) -> str:
    return f"{MONTHS[d.month - 1]} {d.day}"


def long_label(d: date) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {MONTHS[d.month - 1]} {d.day}"


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------

def _checkbox(dr, x, y, size, done=False):
    dr.rectangle([x, y, x + size, y + size], outline=BLACK, width=2)
    if done:
        dr.rectangle([x, y, x + size, y + size], fill=BLACK)
        dr.line([x + 4, y + size * 0.55, x + size * 0.42, y + size - 4], fill=WHITE, width=2)
        dr.line([x + size * 0.42, y + size - 4, x + size - 3, y + 3], fill=WHITE, width=2)


def _truncate(dr, text, font, maxw):
    if dr.textlength(text, font=font) <= maxw:
        return text
    while text and dr.textlength(text + "…", font=font) > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def _divider(dr, x0, x1, y, heavy=False):
    # 1-bit e-paper: a light-gray hairline dithers away, so a "light" rule is a
    # solid-black DASHED line — every pixel is full black (survives the panel) while
    # the gaps still read as secondary next to the heavy solid rule.
    if heavy:
        dr.line([x0, y, x1, y], fill=BLACK, width=2)
    else:
        x = x0
        while x < x1:
            dr.line([x, y, min(x + 5, x1), y], fill=BLACK, width=1)
            x += 9
    return y


def _vdashed(dr, x, y0, y1):
    y = y0
    while y < y1:
        dr.line([x, y, x, min(y + 5, y1)], fill=BLACK, width=1)
        y += 9


# ---------------------------------------------------------------------------
# blocks — each returns the y coordinate after it
# ---------------------------------------------------------------------------

def _mini_battery(dr, x, y_mid, level, w=15, h=25):
    """Small vertical battery glyph filled to `level` percent, centered on y_mid."""
    top = y_mid - h / 2
    dr.rounded_rectangle([x + w * 0.28, top, x + w * 0.72, top + 4], radius=1, fill=BLACK)  # nub
    by0, by1 = top + 4, top + h
    dr.rounded_rectangle([x, by0, x + w, by1], radius=3, outline=BLACK, width=2)
    lvl = max(0, min(100, int(level)))
    if lvl > 0:
        inset = 3
        fy1 = by1 - inset
        fy0 = fy1 - lvl / 100 * (by1 - inset - (by0 + inset))
        dr.rounded_rectangle([x + inset, fy0, x + w - inset, fy1], radius=1, fill=BLACK)


def _mini_thermo(dr, x, y_mid, w=12, h=25):
    """Small filled thermometer silhouette, centered on y_mid."""
    cx = x + w / 2
    top = y_mid - h / 2
    rb = w * 0.55
    cy = top + h - rb
    dr.rounded_rectangle([cx - 3, top, cx + 3, cy], radius=3, fill=BLACK)  # stem
    dr.ellipse([cx - rb, cy - rb, cx + rb, cy + rb], fill=BLACK)           # bulb


def _header(dr, x0, x1, F, data):
    fs = F["meta"]
    batt = data.get("battery")

    # LEFT: battery + thermometer glyphs stacked. No numbers drawn — a blank gap
    # is left to the right of each so you can overlay the real values as text
    # widgets in SenseCraft.
    # LEFT: date.
    dr.text((x0, 16), data["date_label"], font=F["date"], fill=BLACK, anchor="lt")

    # MIDDLE: open count + next refresh on one line, centered.
    midx = (x0 + x1) / 2
    when = data.get("next_refresh", data.get("updated", ""))
    dr.text((midx, 27), f"{data['open_count']} open   ·   Next Refresh: {when}",
            font=fs, fill=BLACK, anchor="mm")

    # RIGHT: thermometer + battery on one line, with a blank gap after each glyph
    # for the real values you overlay as text widgets in SenseCraft.
    ymid, num_space, tw, bw = 27, 44, 13, 16
    rx = x1 - ((tw + 4 + num_space) + 14 + (bw + 4 + num_space))
    _mini_thermo(dr, rx, ymid, w=tw, h=24)
    rx += tw + 4 + num_space + 14
    _mini_battery(dr, rx, ymid, batt if batt is not None else 80, w=bw, h=24)

    return _divider(dr, x0, x1, 50, heavy=True)


def _weeks(data, style):
    today = data["date"]
    if style == "month":
        cc = _cal.Calendar(firstweekday=6)  # Sunday first
        return [[(dt, dt.month == today.month) for dt in wk]
                for wk in cc.monthdatescalendar(today.year, today.month)]
    start = today - timedelta(days=(today.weekday() + 1) % 7)  # Sunday of this week
    days = [start + timedelta(days=i) for i in range(14)]
    return [[(dt, True) for dt in days[0:7]], [(dt, True) for dt in days[7:14]]]


def _calendar(dr, x, y, w, F, data, style):
    today = data["date"]
    weeks = _weeks(data, style)
    if style == "month":
        label, sub = f"{MONTHS[today.month - 1]} {today.year}", "Today · " + short_date(today)
        row_h, r, fday = 21, 10, F["cal_sm"]
    else:
        first, last = weeks[0][0][0], weeks[1][6][0]
        label, sub = "This week & next", f"{short_date(first)} – {short_date(last)}"
        row_h, r, fday = 30, 14, F["cal"]

    dr.text((x, y), label, font=F["h2"], fill=BLACK)
    dr.text((x + w, y), sub, font=F["meta"], fill=BLACK, anchor="rt")
    y += 26
    cw = w / 7
    for c, ch in enumerate("SMTWTFS"):
        dr.text((x + c * cw + cw / 2, y), ch, font=F["cal_wd"], fill=BLACK, anchor="mt")
    y += 20

    events = data["events_by_day"]
    for wk in weeks:
        cy = y + row_h / 2
        for c, (dt, in_scope) in enumerate(wk):
            cx = x + c * cw + cw / 2
            if dt == today:
                dr.ellipse([cx - r, cy - r, cx + r, cy + r], fill=BLACK)
                dr.text((cx, cy), str(dt.day), font=fday, fill=WHITE, anchor="mm")
            elif not in_scope:
                continue  # month spillover: leave the cell blank (no dim gray on 1-bit)
            else:
                dr.text((cx, cy), str(dt.day), font=fday, fill=BLACK, anchor="mm")
                if dt.isoformat() in events:
                    dot = cy + row_h / 2 - 2
                    dr.ellipse([cx - 2, dot - 2, cx + 2, dot + 2], fill=BLACK)
        y += row_h
    return y


def _upcoming(dr, x, y, w, y_bottom, F, data, cap=None):
    dr.text((x, y), "UPCOMING", font=F["sec"], fill=BLACK)
    _divider(dr, x, x + w, y + 18)
    y += 30
    events = data["upcoming"]
    if not events:
        dr.text((x, y), "· nothing scheduled", font=F["up"], fill=BLACK)
        return y + 24
    items = events[:cap] if cap else events
    row_h, shown = 26, 0
    for e in items:
        if y + row_h > y_bottom - 20:  # keep room for a "+N more" line
            break
        dr.ellipse([x, y + 3, x + 6, y + 9], fill=BLACK)
        line = _truncate(dr, f"{e['title']} — {e['when']}", F["up"], w - 16)
        dr.text((x + 14, y), line, font=F["up"], fill=BLACK)
        y += row_h
        shown += 1
    more = len(events) - shown
    if more > 0:
        dr.text((x, y + 2), f"+ {more} more upcoming", font=F["meta"], fill=BLACK)
        y += 24
    return y


LOG_H = 19


def _log(dr, x, y, w, F, lg):
    """One log line, mirroring the web UI: `└ 07-06 11:25 · note`. The elbow is
    drawn (not a glyph) so it never depends on the panel font having box-drawing."""
    dr.line([x + 2, y - 2, x + 2, y + 9], fill=BLACK, width=1)
    dr.line([x + 2, y + 9, x + 9, y + 9], fill=BLACK, width=1)
    lx = x + 14
    stamp = lg["when"]
    dr.text((lx, y), stamp, font=F["logb"], fill=BLACK)
    off = dr.textlength(stamp, font=F["logb"])
    dr.text((lx + off, y), _truncate(dr, " · " + lg["text"], F["log"], w - 14 - off),
            font=F["log"], fill=BLACK)


def _task_block(dr, x, y, w, y_bottom, F, t, reserve, max_logs):
    """A task with its logs, subtasks, and each subtask's logs. Returns the new y,
    or None if the task header itself didn't fit (caller stops and shows '+ N more')."""
    box, sbox, task_h, sub_h = 17, 12, 27, 23
    if y + task_h > y_bottom - reserve:
        return None
    _checkbox(dr, x, y + 1, box)
    tx = x + box + 14
    title = ("! " if t.get("blocked") else "") + t["title"]
    dr.text((tx, y), _truncate(dr, title, F["row"], w - box - 14 - 78), font=F["row"], fill=BLACK)
    if t.get("category"):
        dr.text((x + w, y + 2), t["category"], font=F["cat"], fill=BLACK, anchor="rt")
    y += task_h
    # logs belonging to the task itself
    for lg in t.get("logs", [])[-max_logs:]:
        if y + LOG_H > y_bottom - reserve:
            return y
        _log(dr, tx, y, x + w - tx, F, lg)
        y += LOG_H
    # subtasks (done hidden), each followed by its own logs
    for s in t.get("subs", []):
        if s.get("done"):
            continue
        if y + sub_h > y_bottom - reserve:
            return y
        _checkbox(dr, tx, y + 2, sbox)
        sx = tx + sbox + 8
        dr.text((sx, y), _truncate(dr, s["title"], F["sub"], x + w - sx), font=F["sub"], fill=BLACK)
        y += sub_h
        for lg in s.get("logs", [])[-max_logs:]:
            if y + LOG_H > y_bottom - reserve:
                return y
            _log(dr, sx, y, x + w - sx, F, lg)
            y += LOG_H
    return y


def _tasks(dr, x, y, w, y_bottom, F, data, max_logs=2):
    reserve = 26
    drawn = [0]
    total = len(data["major"]) + len(data["d2d"])
    if total == 0:
        dr.text((x + w / 2, y + 40), "no active directives", font=F["h2"], fill=BLACK, anchor="mm")
        return

    def section(label, items):
        nonlocal y
        if not items or y + 30 > y_bottom - reserve:
            return
        dr.text((x, y), label, font=F["sec"], fill=BLACK)
        _divider(dr, x, x + w, y + 18)
        y += 28
        for t in items:
            ny = _task_block(dr, x, y, w, y_bottom, F, t, reserve, max_logs)
            if ny is None:
                return
            y = ny + 6
            drawn[0] += 1

    section("MAJOR", data["major"])
    y += 6
    section("DAY-TO-DAY", data["d2d"])
    more = total - drawn[0]
    if more > 0:
        _divider(dr, x, x + w, y + 2)
        dr.text((x, y + 10), f"+ {more} more open task{'s' if more != 1 else ''} — see all in the app",
                font=F["meta"], fill=BLACK)


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------

def render(data: dict, layout: str = "landscape", cal: str = "2week") -> bytes:
    W, H = (480, 800) if layout == "portrait" else (800, 480)
    img = Image.new("L", (W, H), WHITE)
    dr = ImageDraw.Draw(img)
    F = {
        "date": _font(24, bold=True), "h2": _font(17, bold=True),
        "sec": _font(13, bold=True), "row": _font(17), "cat": _font(12),
        "cal": _font(15), "cal_sm": _font(13), "cal_wd": _font(11),
        "up": _font(15), "meta": _font(13), "sub": _font(14),
        "log": _font(13), "logb": _font(13, bold=True),
    }
    m = MARGIN
    y = _header(dr, m, W - m, F, data)

    if layout == "portrait":
        cy = _calendar(dr, m, y + 20, W - 2 * m, F, data, cal)
        _divider(dr, m, W - m, cy + 8, heavy=True)
        uy = _upcoming(dr, m, cy + 18, W - 2 * m, H, F, data, cap=3)
        _divider(dr, m, W - m, uy + 6, heavy=True)
        _tasks(dr, m, uy + 16, W - 2 * m, H - m, F, data)
    else:
        rx = int(W * 0.56)
        rw = W - m - rx
        cy = _calendar(dr, rx, y + 16, rw, F, data, cal)
        _divider(dr, rx, W - m, cy + 8, heavy=True)
        _upcoming(dr, rx, cy + 18, rw, H - m, F, data)
        _vdashed(dr, rx - 18, y + 12, H - m)
        _tasks(dr, m, y + 16, rx - 18 - m - 8, H - m, F, data)

    # Flatten to true 1-bit with a hard threshold (no dithering) so the panel shows
    # crisp black/white — grays (secondary text) snap to solid black instead of the
    # faded dot pattern the device produces when it dithers grayscale itself.
    img = img.convert("1", dither=Image.NONE)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
