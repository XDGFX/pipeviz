"""pipeviz — plumbing diagram generation from YAML source files."""

__version__ = "0.1.0"
APP_NAME = "pipeviz"
APP_URL = "https://github.com/xdgfx/pipeviz"

# Re-export public API so callers can do `from pipeviz import <name>`.
from pipeviz.pv_colors import (  # noqa: F401
    NAMED_COLORS,
    SERVICE_COLORS,
    _pipe_edge_attrs,
    parse_size_mm,
    penwidth_from_mm,
    resolve_color,
)
from pipeviz.pv_gv_html import (  # noqa: F401
    build_html_label,
    build_pipe_html_label,
    dot_quote,
    normalise_ports,
    render_component_node,
)
from pipeviz.PlumbingSystem import PlumbingSystem  # noqa: F401
from pipeviz.pipeviz import (  # noqa: F401
    build_dot,
    deep_merge,
    load_yaml_file,
    parse,
    parse_connection_token,
    resolve_component,
    resolve_template,
    validate_connections_chain,
    validate_diagram,
    write_graphviz_output,
)
