"""Colour resolution and pipe-size-to-penwidth utilities for pipeviz."""

import re as _re

# WireViz-compatible DIN 2-letter colour codes → hex.
NAMED_COLORS: dict[str, str] = {
    "BK": "#000000",  # black
    "WH": "#ffffff",  # white
    "GY": "#999999",  # grey
    "PK": "#ff66cc",  # pink
    "RD": "#ff0000",  # red
    "OG": "#ff8000",  # orange
    "YE": "#ffff00",  # yellow
    "OL": "#708000",  # olive green
    "GN": "#00ff00",  # green
    "TQ": "#00ffff",  # turquoise
    "LB": "#a0dfff",  # light blue
    "BU": "#0066ff",  # blue
    "VT": "#8000ff",  # violet
    "BN": "#895956",  # brown
    "BG": "#ceb673",  # beige
    "IV": "#f5f0d0",  # ivory
    "SL": "#708090",  # slate
    "CU": "#d6775e",  # copper
    "SN": "#aaaaaa",  # tin
    "SR": "#84878c",  # silver
    "GD": "#ffcf80",  # gold
}

# Maps service_rating string → (fill_code, border_code) using WireViz 2-letter codes.
# The border colour doubles as the edge colour for pipe runs with that rating.
SERVICE_COLORS: dict[str, tuple[str, str]] = {
    "potable": ("LB", "LB"),
    "waste": ("GY", "RD"),
    "vent": ("BG", "OL"),
    "hot": ("GD", "OG"),
}


def resolve_color(value: str) -> str:
    """Resolve a colour: WireViz 2-letter code → hex, or pass hex through."""
    upper = value.strip().upper()
    if upper in NAMED_COLORS:
        return NAMED_COLORS[upper]
    return value


def parse_size_mm(size: str | None) -> float | None:
    """Parse a size string to millimetres. Returns None if not parseable."""
    if size is None:
        return None
    s = str(size).strip()
    m = _re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*mm$", s, _re.IGNORECASE)
    if m:
        return float(m.group(1))
    m = _re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*(?:in|inch|inches|")', s, _re.IGNORECASE)
    if m:
        return float(m.group(1)) * 25.4
    return None


def penwidth_from_mm(mm: float) -> float:
    """Map a pipe diameter in mm to a Graphviz penwidth, clamped to [1.0, 32.0]."""
    return max(1.0, min(32.0, mm / 3.0))


def _pipe_edge_attrs(pipe_spec: dict, extra_attrs: dict | None = None) -> str:
    """Return a DOT attribute string for edges adjacent to a pipe node.

    Handles colour (explicit > service_rating) and penwidth (from size).
    ``extra_attrs`` are merged in last. Returns empty string if no styling applies.
    """
    attrs = {}

    raw_colour = pipe_spec.get("colour") or pipe_spec.get("color")
    if raw_colour:
        attrs["color"] = resolve_color(str(raw_colour))
    else:
        service = pipe_spec.get("service_rating", "")
        if service in SERVICE_COLORS:
            _, border_code = SERVICE_COLORS[service]
            attrs["color"] = resolve_color(border_code)

    size_mm = parse_size_mm(pipe_spec.get("size"))
    if size_mm is not None:
        attrs["penwidth"] = f"{penwidth_from_mm(size_mm):.2f}"

    if extra_attrs:
        attrs.update(extra_attrs)

    if not attrs:
        return ""
    parts = ", ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"[{parts}]"
