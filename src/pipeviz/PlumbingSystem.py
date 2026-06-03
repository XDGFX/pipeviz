"""PlumbingSystem: converts a resolved diagram dict into Graphviz DOT text."""

from pathlib import Path

from pipeviz.pv_colors import SERVICE_COLORS, _pipe_edge_attrs, resolve_color
from pipeviz.pv_gv_html import (
    GRAPHVIZ_FONT,
    build_pipe_html_label,
    dot_quote,
    normalise_ports,
    render_component_node,
)

GRAPHVIZ_DEFAULTS = {
    "rankdir": "LR",
    "splines": "spline",
    "bgcolor": "#FFFFFF",
}


class PlumbingSystem:
    """Wraps a resolved diagram dict and renders it to Graphviz DOT."""

    def __init__(self, diagram: dict, file_path) -> None:
        self.diagram = diagram
        self.file_path = file_path

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_dot(self) -> str:
        """Convert the resolved diagram into Graphviz DOT text."""
        from pipeviz.pipeviz import parse_connection_token, validate_connections_chain

        diagram = self.diagram
        file_path = self.file_path

        graph_defaults = diagram.get("diagram", {})
        title = graph_defaults.get(
            "title", Path(file_path).stem.replace("_", " ").title()
        )
        rankdir = graph_defaults.get("rankdir", GRAPHVIZ_DEFAULTS["rankdir"])
        splines = graph_defaults.get("splines", GRAPHVIZ_DEFAULTS["splines"])
        bgcolor = resolve_color(
            graph_defaults.get("bgcolor", GRAPHVIZ_DEFAULTS["bgcolor"])
        )
        ranksep = graph_defaults.get("ranksep", "2")
        nodesep = graph_defaults.get("nodesep", "0.33")
        fontname = graph_defaults.get("fontname", GRAPHVIZ_FONT)

        lines = ["digraph G {"]
        lines.append(
            f"  graph [rankdir={dot_quote(rankdir)}, splines={dot_quote(splines)}, "
            f"bgcolor={dot_quote(bgcolor)}, fontname={dot_quote(fontname)}, "
            f"ranksep={dot_quote(ranksep)}, nodesep={dot_quote(nodesep)}];"
        )
        lines.append(
            f'  node [fillcolor="#FFFFFF" fontname={dot_quote(fontname)} height=0 margin=0 shape=none style=filled width=0];'
        )
        lines.append(f"  edge [fontname={dot_quote(fontname)}, style=bold, dir=none];")
        lines.append('  labelloc="t";')
        lines.append(f"  label={dot_quote(title)};")
        lines.append("  fontsize=20;")
        lines.append("")

        connections = diagram.get("connections", [])
        pipes_spec = diagram.get("pipes", {})
        component_names = set(diagram["components"].keys())
        pipe_names = set(pipes_spec.keys())

        emitted_nodes: set = set()
        anon_counter = 0
        pipe_counter = 0

        for chain_idx, chain in enumerate(connections):
            try:
                hops = validate_connections_chain(chain, component_names, pipe_names)
            except ValueError as exc:
                raise ValueError(
                    f"{file_path}: connections[{chain_idx}] {chain}: {exc}"
                ) from exc

            token_info = []
            for token in chain:
                parsed = parse_connection_token(token)
                base = parsed["base_name"]
                port = parsed["port"]
                instance = parsed["instance"]

                if base in pipe_names:
                    node_id = f"{base}__{pipe_counter}"
                    pipe_counter += 1
                    token_info.append(
                        {
                            "node_id": node_id,
                            "base": base,
                            "port": port,
                            "is_pipe": True,
                            "flip_after": parsed["reversed"],
                        }
                    )
                else:
                    if instance is None:
                        node_id = base
                    elif instance == "":
                        node_id = f"{base}__{anon_counter}"
                        anon_counter += 1
                    else:
                        node_id = f"{base}__{instance}"
                    token_info.append(
                        {
                            "node_id": node_id,
                            "base": base,
                            "port": port,
                            "is_pipe": False,
                            "flip_after": False,
                        }
                    )

            for ti in token_info:
                if ti["node_id"] not in emitted_nodes:
                    if ti["is_pipe"]:
                        pipe_html = build_pipe_html_label(
                            ti["base"], pipes_spec[ti["base"]]
                        )
                        lines.append(
                            f'  {dot_quote(ti["node_id"])} [shape=none, margin=0, label={pipe_html}];'
                        )
                    else:
                        lines.append(
                            render_component_node(
                                ti["node_id"], diagram["components"][ti["base"]]
                            )
                        )
                    emitted_nodes.add(ti["node_id"])

            reversed_state = False
            for hop_idx in range(len(hops)):
                fi = token_info[hop_idx]
                ti = token_info[hop_idx + 1]

                at_flip = fi["is_pipe"] and fi.get("flip_after", False)
                pre_flip = reversed_state
                if at_flip:
                    reversed_state = True
                    if (
                        hop_idx >= 1
                        and not token_info[hop_idx - 1]["is_pipe"]
                        and not ti["is_pipe"]
                    ):
                        prev_id = dot_quote(token_info[hop_idx - 1]["node_id"])
                        next_id = dot_quote(ti["node_id"])
                        lines.append(f"  {{rank=same; {prev_id}; {next_id}}}")
                post_flip = reversed_state

                if fi["is_pipe"]:
                    if at_flip:
                        tail = f'{dot_quote(fi["node_id"])}:s'
                    elif pre_flip:
                        tail = f'{dot_quote(fi["node_id"])}:w'
                    else:
                        tail = f'{dot_quote(fi["node_id"])}:e'
                else:
                    port = fi["port"]
                    if port is None:
                        comp_ports = normalise_ports(diagram["components"][fi["base"]])
                        if comp_ports:
                            port = comp_ports[0]["name"]
                    side = "w" if pre_flip else "e"
                    if port:
                        tail = f'{dot_quote(fi["node_id"])}:{port}__{side}:{side}'
                    elif diagram["components"][fi["base"]].get("simple"):
                        tail = f'{dot_quote(fi["node_id"])}:{side}'
                    else:
                        tail = dot_quote(fi["node_id"])

                if ti["is_pipe"]:
                    if ti.get("flip_after", False):
                        head = f'{dot_quote(ti["node_id"])}:n'
                    elif post_flip:
                        head = f'{dot_quote(ti["node_id"])}:e'
                    else:
                        head = f'{dot_quote(ti["node_id"])}:w'
                else:
                    port = ti["port"]
                    if port is None:
                        comp_ports = normalise_ports(diagram["components"][ti["base"]])
                        if comp_ports:
                            port = comp_ports[0]["name"]
                    side = "e" if post_flip else "w"
                    if port:
                        head = f'{dot_quote(ti["node_id"])}:{port}__{side}:{side}'
                    elif diagram["components"][ti["base"]].get("simple"):
                        head = f'{dot_quote(ti["node_id"])}:{side}'
                    else:
                        head = dot_quote(ti["node_id"])

                pipe_base = (
                    fi["base"]
                    if fi["is_pipe"]
                    else (ti["base"] if ti["is_pipe"] else None)
                )
                extra = {"constraint": "false"} if post_flip else None
                edge_attrs = (
                    _pipe_edge_attrs(pipes_spec[pipe_base], extra)
                    if pipe_base
                    else ('[constraint="false"]' if extra else "")
                )
                suffix = f" {edge_attrs}" if edge_attrs else ""
                lines.append(f"  {tail} -> {head}{suffix};")

        lines.append("}")
        return "\n".join(lines) + "\n"
