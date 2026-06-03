"""Graphviz HTML-label builders for pipeviz components and pipe nodes."""

from html import escape

from pipeviz.pv_colors import SERVICE_COLORS, resolve_color

GRAPHVIZ_FONT = "JetBrains Mono"


def dot_quote(value) -> str:
    """Quote a value for Graphviz DOT attributes."""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def normalise_ports(component_spec: dict) -> list[dict]:
    """Return the port list for a component as a list of dicts with at least a 'name' key."""
    if "ports" in component_spec:
        ports = component_spec["ports"]
        if isinstance(ports, dict):
            return [{"name": k} for k in ports.keys()]
        if isinstance(ports, list):
            return [p if isinstance(p, dict) else {"name": str(p)} for p in ports]
        return []
    portcount = component_spec.get("portcount")
    if portcount:
        return [{"name": str(i)} for i in range(1, portcount + 1)]
    return []


def build_html_label(node_id: str, component_spec: dict) -> str:
    """Build a Graphviz HTML label for a component with named ports."""
    label = escape(str(component_spec.get("label", node_id)))
    ports = normalise_ports(component_spec)
    fill_color = resolve_color(component_spec.get("fillcolor", "#e2e8f0"))
    border_color = resolve_color(component_spec.get("color", "#64748b"))

    ncols = 3  # port name | connection size | gender
    rows = []

    rows.append(
        f'<TR><TD COLSPAN="{ncols}" BORDER="1" BGCOLOR="{escape(fill_color)}" '
        f'COLOR="{escape(border_color)}" ALIGN="CENTER">{label}</TD></TR>'
    )

    meta_parts = []
    for key in ("manufacturer", "model", "mpn", "supplier"):
        val = component_spec.get(key)
        if val:
            meta_parts.append(escape(str(val)))
    if meta_parts:
        rows.append(
            f'<TR><TD COLSPAN="{ncols}" BORDER="1" ALIGN="CENTER">'
            f'{" &middot; ".join(meta_parts)}</TD></TR>'
        )

    for port in ([] if component_spec.get("simple") else ports):
        port_name = str(port["name"])
        size_text = escape(str(port.get("connection_size", "")))
        gender_text = escape(str(port.get("gender", "")))
        rows.append(
            f"<TR>"
            f'<TD PORT="{escape(port_name)}__w" BORDER="1" ALIGN="CENTER">{escape(port_name)}</TD>'
            f'<TD BORDER="1" ALIGN="CENTER">{size_text}</TD>'
            f'<TD PORT="{escape(port_name)}__e" BORDER="1" ALIGN="CENTER">{gender_text}</TD>'
            f"</TR>"
        )

    desc = str(component_spec.get("description", "")).strip()
    if desc:
        desc_clean = " ".join(desc.split())
        if len(desc_clean) > 80:
            desc_clean = desc_clean[:77] + "..."
        rows.append(
            f'<TR><TD COLSPAN="{ncols}" BORDER="1" ALIGN="CENTER">'
            f"{escape(desc_clean)}</TD></TR>"
        )

    rows_html = "\n".join(f"  {r}" for r in rows)
    return (
        '<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="3">\n'
        f"{rows_html}\n"
        "</TABLE>>"
    )


def build_pipe_html_label(pipe_name: str, pipe_spec: dict) -> str:
    """Build a Graphviz HTML label for a pipe segment."""
    label = escape(str(pipe_spec.get("label", pipe_name)))
    service = pipe_spec.get("service_rating", "")
    raw_fill, raw_border = SERVICE_COLORS.get(service, ("#f1f5f9", "#64748b"))
    fill_color, border_color = resolve_color(raw_fill), resolve_color(raw_border)

    rows = []
    rows.append(
        f'<TR><TD BORDER="1" BGCOLOR="{fill_color}" COLOR="{border_color}" ALIGN="CENTER">'
        f"{label}</TD></TR>"
    )

    meta_parts = []
    for key in ("size", "material"):
        val = pipe_spec.get(key)
        if val:
            meta_parts.append(escape(str(val)))
    if service:
        meta_parts.append(escape(str(service)))
    if meta_parts:
        rows.append(
            f'<TR><TD BORDER="1" ALIGN="LEFT">{" &middot; ".join(meta_parts)}</TD></TR>'
        )

    rows_html = "\n".join(f"  {r}" for r in rows)
    return (
        '<<TABLE BORDER="0" CELLSPACING="0" CELLPADDING="0">\n'
        f"{rows_html}\n"
        "</TABLE>>"
    )


def render_component_node(node_id: str, component_spec: dict) -> str:
    """Render a component into a DOT node statement."""
    ports = normalise_ports(component_spec)
    node_color = resolve_color(component_spec.get("color", "#334155"))
    fill_color = resolve_color(component_spec.get("fillcolor", "#e2e8f0"))
    shape = component_spec.get("shape", "box")
    style = component_spec.get("style", "rounded,filled")
    fontname = component_spec.get("fontname", GRAPHVIZ_FONT)
    label = component_spec.get("label", node_id)

    if ports or component_spec.get("simple"):
        html_label = build_html_label(node_id, component_spec)
        return (
            f"  {dot_quote(node_id)} "
            f"[fontname={dot_quote(fontname)}, shape=none, margin=0, label={html_label}];"
        )

    return (
        f"  {dot_quote(node_id)} "
        f"[shape={dot_quote(shape)}, style={dot_quote(style)}, "
        f"fillcolor={dot_quote(fill_color)}, color={dot_quote(node_color)}, "
        f"fontname={dot_quote(fontname)}, label={dot_quote(label)}];"
    )
