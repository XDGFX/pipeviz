"""
Core pipeviz logic: YAML loading, template/ref resolution, validation,
connection parsing, and Graphviz output writing.
"""

import re
import subprocess
from copy import deepcopy
from html import escape
from pathlib import Path

import yaml

from pipeviz.PlumbingSystem import PlumbingSystem
from pipeviz.pv_colors import SERVICE_COLORS, resolve_color
from pipeviz.pv_gv_html import normalise_ports


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml_file(file_path) -> dict:
    """Load a YAML file and return an empty mapping when the file is blank."""
    with open(file_path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def deep_merge(base, overlay):
    """Recursively merge dicts without mutating the inputs."""
    if not isinstance(base, dict):
        return deepcopy(overlay)
    if not isinstance(overlay, dict):
        return deepcopy(overlay)
    merged = deepcopy(base)
    for key, value in overlay.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


# ---------------------------------------------------------------------------
# Template / component resolution
# ---------------------------------------------------------------------------

def resolve_template(template_name: str, templates: dict, stack=None) -> dict:
    """Resolve a template, following any nested template chain."""
    stack = stack or []
    if template_name in stack:
        chain = " -> ".join(stack + [template_name])
        raise ValueError(f"Template cycle detected: {chain}")
    if template_name not in templates:
        raise ValueError(f"Unknown template: {template_name}")
    template = deepcopy(templates[template_name])
    parent_template = template.pop("template", None)
    if parent_template:
        template = deep_merge(
            resolve_template(parent_template, templates, stack + [template_name]),
            template,
        )
    return template


def resolve_component(
    component_name: str,
    component_spec,
    templates: dict,
    component_library: dict,
    stack=None,
) -> dict:
    """Resolve a component spec against shared refs and templates."""
    stack = stack or []
    if component_name in stack:
        chain = " -> ".join(stack + [component_name])
        raise ValueError(f"Component cycle detected: {chain}")

    resolved = deepcopy(component_spec) if isinstance(component_spec, dict) else {}

    reference_name = resolved.pop("ref", None)
    if reference_name:
        if reference_name not in component_library:
            raise ValueError(f"Unknown component reference: {reference_name}")
        resolved = deep_merge(
            resolve_component(
                reference_name,
                component_library[reference_name],
                templates,
                component_library,
                stack + [component_name],
            ),
            resolved,
        )

    template_name = resolved.pop("template", None)
    if template_name:
        resolved = deep_merge(resolve_template(template_name, templates), resolved)

    return resolved


# ---------------------------------------------------------------------------
# Connection token parsing and chain validation
# ---------------------------------------------------------------------------

def parse_connection_token(token: str) -> dict:
    """Parse a connection chain token into base_name, instance, and port components.

    A trailing ``^`` on the name part marks a pipe as a reversal point — the
    outgoing edge and all subsequent hops in the chain flip direction (L↔R).
    ``^`` is stripped before further parsing; it only has effect on pipe tokens.
    """
    if not token:
        raise ValueError("Connection token must not be empty")

    colon_parts = token.split(":", 1)
    name_part = colon_parts[0]
    port_part = colon_parts[1] if len(colon_parts) > 1 else None

    if port_part is not None:
        if port_part.startswith("[") or "," in port_part:
            raise ValueError(
                "Multi-port list syntax is invalid; at most one port per token"
            )
        if re.search(r"^\d+-\d+$", port_part):
            raise ValueError(
                "Multi-port range syntax is invalid; at most one port per token"
            )

    reversed_marker = name_part.endswith("^")
    if reversed_marker:
        name_part = name_part[:-1]

    if "." in name_part:
        dot_idx = name_part.index(".")
        base_name = name_part[:dot_idx]
        instance = name_part[dot_idx + 1:]
    else:
        base_name = name_part
        instance = None

    if not base_name:
        raise ValueError("Connection token must have a non-empty base name")

    return {
        "base_name": base_name,
        "instance": instance,
        "port": port_part,
        "reversed": reversed_marker,
    }


def validate_connections_chain(
    chain: list,
    component_names: set,
    pipe_names: set,
) -> list:
    """Validate one connections chain and return the hops it produces."""
    if len(chain) < 2:
        raise ValueError("At least two tokens are required in a connection chain")

    def classify(token: str) -> tuple:
        parsed = parse_connection_token(token)
        base = parsed["base_name"]
        if base in component_names:
            return parsed, "component"
        if base in pipe_names:
            return parsed, "pipe"
        raise ValueError(f"Unknown name '{base}' not found in components or pipes")

    parsed_tokens = []
    for i, t in enumerate(chain):
        try:
            parsed_tokens.append(classify(t))
        except ValueError as exc:
            raise ValueError(f"token[{i}] {t!r}: {exc}") from exc

    hops = []
    for i in range(len(parsed_tokens) - 1):
        from_parsed, from_kind = parsed_tokens[i]
        to_parsed, to_kind = parsed_tokens[i + 1]
        if from_kind == "pipe" and to_kind == "pipe":
            raise ValueError(
                f"Pipe-to-pipe adjacent hops are invalid: "
                f"'{from_parsed['base_name']}' -> '{to_parsed['base_name']}'"
            )
        hops.append(
            {
                "from": from_parsed,
                "to": to_parsed,
                "from_kind": from_kind,
                "to_kind": to_kind,
            }
        )
    return hops


# ---------------------------------------------------------------------------
# Diagram validation
# ---------------------------------------------------------------------------

def validate_diagram(diagram: dict, file_path) -> None:
    """Validate the resolved diagram structure before rendering."""
    components = diagram.get("components")
    if not isinstance(components, dict) or not components:
        raise ValueError(
            f"{file_path}: diagram must define a non-empty 'components' mapping"
        )

    connections = diagram.get("connections")
    if not isinstance(connections, list) or not connections:
        raise ValueError(
            f"{file_path}: diagram must define a non-empty 'connections' list"
        )

    for component_name, component_spec in components.items():
        if not isinstance(component_spec, dict):
            raise ValueError(
                f"{file_path}: component '{component_name}' must be a mapping"
            )
        if not component_spec.get("label"):
            raise ValueError(
                f"{file_path}: component '{component_name}' must define a label"
            )
        is_simple = bool(component_spec.get("simple"))
        has_ports = "ports" in component_spec
        has_portcount = "portcount" in component_spec
        if is_simple:
            if has_ports or has_portcount:
                raise ValueError(
                    f"{file_path}: simple component '{component_name}' must not define 'ports' or 'portcount'"
                )
        else:
            if not has_ports and not has_portcount:
                raise ValueError(
                    f"{file_path}: component '{component_name}' must define 'ports' or 'portcount'"
                )
            if has_ports and has_portcount:
                port_list = normalise_ports(component_spec)
                if component_spec["portcount"] != len(port_list):
                    raise ValueError(
                        f"{file_path}: component '{component_name}' portcount "
                        f"{component_spec['portcount']} does not match ports length {len(port_list)}"
                    )

    component_names = set(components.keys())
    pipe_names = set(diagram.get("pipes", {}).keys())

    for chain_idx, chain in enumerate(connections):
        try:
            validate_connections_chain(chain, component_names, pipe_names)
        except ValueError as exc:
            raise ValueError(
                f"{file_path}: connections[{chain_idx}] {chain}: {exc}"
            ) from exc

        for token in chain:
            try:
                parsed = parse_connection_token(token)
            except ValueError as exc:
                raise ValueError(
                    f"{file_path}: connections[{chain_idx}] {chain}, token {token!r}: {exc}"
                ) from exc
            base = parsed["base_name"]
            port = parsed["port"]
            if base in component_names and port is not None:
                if components[base].get("simple"):
                    raise ValueError(
                        f"{file_path}: simple component '{base}' does not support named port references in connections"
                    )
                comp_ports = normalise_ports(components[base])
                port_names = {p["name"] for p in comp_ports}
                if comp_ports and port not in port_names:
                    raise ValueError(
                        f"{file_path}: component '{base}' has no port named '{port}'"
                    )


# ---------------------------------------------------------------------------
# Output writing
# ---------------------------------------------------------------------------

def write_graphviz_output(dot_text: str, format_type: str, output_path) -> None:
    """Render DOT text to the requested output format."""
    if format_type == "gv":
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(dot_text)
        return

    if format_type == "html":
        svg_result = subprocess.run(
            ["dot", "-Tsvg"],
            input=dot_text,
            capture_output=True,
            check=True,
            text=True,
            encoding="utf-8",
        )
        html_text = (
            "<!doctype html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '  <meta charset="utf-8">\n'
            f"  <title>{escape(Path(output_path).stem)}</title>\n"
            "  <style>body{margin:0;padding:1rem;background:#fff;font-family:system-ui,sans-serif;}"
            "svg{max-width:100%;height:auto;}</style>\n"
            "</head>\n"
            "<body>\n"
            f"{svg_result.stdout}\n"
            "</body>\n"
            "</html>\n"
        )
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(html_text)
        return

    is_text_output = format_type != "png"
    result = subprocess.run(
        ["dot", f"-T{format_type}"],
        input=dot_text if is_text_output else dot_text.encode("utf-8"),
        capture_output=True,
        check=True,
        text=is_text_output,
        encoding="utf-8" if is_text_output else None,
    )

    if format_type == "png":
        if not isinstance(result.stdout, (bytes, bytearray)):
            raise TypeError("Graphviz PNG output must be binary")
        with open(output_path, "wb") as handle:
            handle.write(result.stdout)
    else:
        if not isinstance(result.stdout, str):
            raise TypeError("Graphviz text output must be str")
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(result.stdout)


# ---------------------------------------------------------------------------
# Main parse entry point (mirrors wireviz.parse())
# ---------------------------------------------------------------------------

def parse(
    file_path,
    prepend_paths: list | None = None,
    format_type: str = "svg",
    output_dir=None,
    output_name: str | None = None,
) -> None:
    """Parse a pipeviz YAML file and render output.

    Parameters
    ----------
    file_path:
        Path to the diagram YAML file.
    prepend_paths:
        Optional list of YAML files whose contents are merged before the
        diagram data (provides shared component libraries and templates).
    format_type:
        Output format — ``"svg"``, ``"png"``, ``"html"``, or ``"gv"``.
    output_dir:
        Directory for output files.  Defaults to the same directory as
        ``file_path``.
    output_name:
        Base filename (without extension).  Defaults to the stem of
        ``file_path``.
    """
    file_path = Path(file_path)
    if output_dir is None:
        output_dir = file_path.parent
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stem = output_name or file_path.stem
    suffix = {"svg": ".svg", "png": ".png", "html": ".html", "gv": ".gv"}[format_type]
    output_path = output_dir / f"{stem}{suffix}"

    # Build shared data from all prepend files, merged left-to-right.
    shared_data: dict = {}
    for p in (prepend_paths or []):
        if Path(p).exists():
            shared_data = deep_merge(shared_data, load_yaml_file(p))

    diagram_data = load_yaml_file(file_path)

    diagram: dict = {
        "diagram": deep_merge(
            shared_data.get("diagram", {}), diagram_data.get("diagram", {})
        ),
    }

    templates = deep_merge(
        shared_data.get("templates", {}), diagram_data.get("templates", {})
    )
    component_library = deep_merge(
        shared_data.get("components", {}), diagram_data.get("components", {})
    )

    resolved_components = {}
    for component_name, component_spec in component_library.items():
        resolved_components[component_name] = resolve_component(
            component_name,
            component_spec,
            templates,
            component_library,
        )

    diagram["components"] = resolved_components
    diagram["connections"] = diagram_data.get("connections", [])
    diagram["pipes"] = diagram_data.get("pipes", {})

    validate_diagram(diagram, file_path)

    system = PlumbingSystem(diagram, file_path)
    dot_text = system.build_dot()

    write_graphviz_output(dot_text, format_type, output_path)


def build_dot(diagram: dict, file_path) -> str:
    """Convenience wrapper: render a resolved diagram dict to DOT text."""
    return PlumbingSystem(diagram, file_path).build_dot()
