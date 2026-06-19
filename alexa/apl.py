"""APL (Alexa Presentation Language) document builders for screen devices.

Renders a retro phosphor-green CRT list on Echo Show, matching the web app's
DIRECTIVES theme. Display-only (no touch handlers yet). Documents are built
fresh per request with the data inlined — simplest path for a self-hosted skill.
"""

GREEN = "#2bff66"       # bright phosphor (titles, markers)
GREEN_BODY = "#7dffa0"  # body text
GREEN_DIM = "#2a8f44"   # metadata, dividers, done items
BG = "#000000"
FONT = "monospace"

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def short_date(iso: str) -> str:
    """'2026-06-21' -> 'Jun 21'."""
    try:
        y, m, d = (int(x) for x in iso.split("-"))
        return f"{_MONTHS[m - 1]} {d}"
    except Exception:
        return iso


def _text(t, color, size, **kw):
    d = {"type": "Text", "text": t, "color": color, "fontSize": size, "fontFamily": FONT}
    d.update(kw)
    return d


def _row(item: dict):
    """item: {marker, title, meta, dim?}"""
    dim = item.get("dim", False)
    return {
        "type": "Container", "direction": "row", "alignItems": "center",
        "paddingTop": "4dp", "paddingBottom": "4dp",
        "items": [
            _text(item.get("marker", "▸"), GREEN_DIM if dim else GREEN, "16dp",
                  paddingRight="10dp"),
            _text(item["title"], GREEN_DIM if dim else GREEN_BODY, "18dp",
                  grow=1, shrink=1, maxLines=1),
            _text(item.get("meta", ""), GREEN_DIM, "13dp"),
        ],
    }


def _empty(msg: str):
    return _text(msg, GREEN_DIM, "16dp", paddingTop="20dp")


def document(title: str, items: list[dict]) -> dict:
    body = [_row(it) for it in items] if items else [_empty("> nothing here_")]
    return {
        "type": "APL",
        "version": "1.6",
        "theme": "dark",
        "mainTemplate": {
            "parameters": [],
            "item": {
                "type": "Container",
                "width": "100vw",
                "height": "100vh",
                "backgroundColor": BG,
                "paddingLeft": "24dp", "paddingRight": "24dp",
                "paddingTop": "16dp", "paddingBottom": "14dp",
                "items": [
                    _text("▌ " + title, GREEN, "22dp", fontWeight="700"),
                    {"type": "Container", "height": "2dp", "backgroundColor": GREEN_DIM,
                     "marginTop": "8dp", "marginBottom": "6dp"},
                    {"type": "Sequence", "grow": 1, "scrollDirection": "vertical",
                     "items": body},
                ],
            },
        },
    }
