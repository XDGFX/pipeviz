"""Slice G: Named colour resolution."""

import pytest
from pipeviz import NAMED_COLORS, resolve_color, build_pipe_html_label, render_component_node, build_html_label, build_dot


def test_named_code_resolves_to_hex():
    assert resolve_color("RD") == "#ff0000"


def test_named_code_case_insensitive():
    assert resolve_color("rd") == "#ff0000"
    assert resolve_color("Rd") == "#ff0000"


def test_hex_string_passes_through():
    assert resolve_color("#dbeafe") == "#dbeafe"
    assert resolve_color("#FFFFFF") == "#FFFFFF"


def test_graphviz_named_colour_passes_through():
    assert resolve_color("white") == "white"
    assert resolve_color("transparent") == "transparent"


@pytest.mark.parametrize("code,expected_hex", list(NAMED_COLORS.items()))
def test_all_palette_entries_resolve(code, expected_hex):
    assert resolve_color(code) == expected_hex
    assert resolve_color(code.lower()) == expected_hex


def test_service_pipe_label_uses_resolved_hex():
    # potable maps to LB (light blue) for both fill and border
    label = build_pipe_html_label("supply", {"label": "Supply", "service_rating": "potable"})
    assert 'BGCOLOR="#a0dfff"' in label
    assert 'COLOR="#a0dfff"' in label


def test_waste_pipe_label_uses_resolved_hex():
    # waste maps to GY (grey) fill / RD (red) border
    label = build_pipe_html_label("drain", {"label": "Drain", "service_rating": "waste"})
    assert 'BGCOLOR="#999999"' in label
    assert 'COLOR="#ff0000"' in label


def test_component_named_fillcolor_in_html_label():
    # A simple component with named fillcolor should emit the resolved hex in its HTML label
    spec = {"label": "Pump", "fillcolor": "RD", "color": "BK", "simple": True}
    label = build_html_label("pump1", spec)
    assert 'BGCOLOR="#ff0000"' in label
    assert 'COLOR="#000000"' in label


def test_component_named_fillcolor_in_dot_node():
    # A component with no ports and not simple renders fillcolor as DOT attribute
    spec = {"label": "Pump", "fillcolor": "RD", "color": "BK"}
    dot = render_component_node("pump1", spec)
    assert 'fillcolor="#ff0000"' in dot
    assert 'color="#000000"' in dot


def test_diagram_bgcolor_named_colour_resolves():
    diagram = {
        "diagram": {"bgcolor": "IV"},
        "components": {
            "pump": {"label": "Pump", "simple": True},
            "tank": {"label": "Tank", "simple": True},
        },
        "connections": [["pump", "tank"]],
    }
    dot = build_dot(diagram, "test.yml")
    assert 'bgcolor="#f5f0d0"' in dot
