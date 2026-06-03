"""
Slice F: simple component toggle
=================================

A component with ``simple: true`` is a lightweight node — it has one implicit
anonymous port for connection routing but its ports are not displayed in the
diagram.  Label and other metadata (manufacturer, description, etc.) ARE shown.

Run these tests with:
  python -m pytest tests/test_slice_f_simple_components.py -v
"""

import pytest

from pipeviz import build_dot, validate_diagram

# --- helpers ------------------------------------------------------------------


def _diag(components, connections=None, pipes=None):
    d = {"components": components, "pipes": pipes or {}}
    d["connections"] = connections or []
    return d


SIMPLE_COMP = {"label": "Joiner", "simple": True}

FULL_COMP = {"label": "Tank", "ports": ["in", "out"]}


# --- validation: simple passes without ports/portcount -----------------------


def test_simple_component_passes_validation_without_ports():
    diag = _diag(
        {"joiner": SIMPLE_COMP, "tank": FULL_COMP},
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    validate_diagram(diag, "test.yml")  # must not raise


# --- validation: simple rejects ports ----------------------------------------


def test_simple_with_ports_raises():
    diag = _diag(
        {
            "joiner": {"label": "Joiner", "simple": True, "ports": ["a", "b"]},
            "tank": FULL_COMP,
        },
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    with pytest.raises(ValueError, match="simple"):
        validate_diagram(diag, "test.yml")


# --- validation: simple rejects portcount ------------------------------------


def test_simple_with_portcount_raises():
    diag = _diag(
        {
            "joiner": {"label": "Joiner", "simple": True, "portcount": 2},
            "tank": FULL_COMP,
        },
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    with pytest.raises(ValueError, match="simple"):
        validate_diagram(diag, "test.yml")


# --- validation: simple rejects named port in connection token ---------------


def test_simple_component_with_named_port_in_connection_raises():
    diag = _diag(
        {"joiner": SIMPLE_COMP, "tank": FULL_COMP},
        connections=[["tank:in", "joiner:1", "tank:out"]],
    )
    with pytest.raises(ValueError, match="simple"):
        validate_diagram(diag, "test.yml")


# --- rendering: simple component produces HTML label without port rows --------


def test_simple_component_dot_has_html_label():
    diag = _diag(
        {"joiner": SIMPLE_COMP, "tank": FULL_COMP},
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    dot = build_dot(diag, "test.yml")
    assert "Joiner" in dot
    assert "shape=none" in dot  # HTML-label path, not plain box


def test_simple_component_dot_has_no_port_anchor():
    diag = _diag(
        {"joiner": SIMPLE_COMP, "tank": FULL_COMP},
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    dot = build_dot(diag, "test.yml")
    # Port anchors like PORT="foo__w" must not appear for the simple node
    assert "joiner" in dot
    assert (
        "__w" not in dot.split("joiner")[1].split("tank")[0]
    )  # no west anchor in joiner section


def test_simple_component_edges_use_east_west_compass():
    diag = _diag(
        {"joiner": SIMPLE_COMP, "tank": FULL_COMP},
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    dot = build_dot(diag, "test.yml")
    import re

    edges = re.findall(r"([^\s]+)\s*->\s*([^\s;]+)", dot)
    joiner_edges = [(f, t) for f, t in edges if "joiner" in f or "joiner" in t]
    assert joiner_edges, "No edges involving joiner found"
    for from_node, to_node in joiner_edges:
        if "joiner" in from_node:
            assert from_node.endswith(
                ":e"
            ), f"Expected :e compass on outgoing joiner edge, got {from_node}"
        if "joiner" in to_node:
            assert to_node.endswith(
                ":w"
            ), f"Expected :w compass on incoming joiner edge, got {to_node}"


# --- rendering: simple component shows metadata fields -----------------------


def test_simple_component_renders_description():
    diag = _diag(
        {
            "joiner": {
                "label": "Joiner",
                "simple": True,
                "description": "Push-fit joiner",
            },
            "tank": FULL_COMP,
        },
        connections=[["tank:in", "joiner", "tank:out"]],
    )
    dot = build_dot(diag, "test.yml")
    assert "Push-fit joiner" in dot
