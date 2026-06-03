"""
Slice H: pipe edge styling
==========================

Edges that flank a pipe node should visually represent the hose:
- ``colour`` (or ``color``) on the pipe spec sets the edge colour
- ``service_rating`` (when no explicit colour) derives the edge colour from
  SERVICE_COLORS (border/vivid colour, second element)
- ``size`` drives ``penwidth`` via a linear mm-based scale

Run these tests with:
  cd /Users/cal/git/truck_2025_plumbing
  python -m pytest tests/test_slice_h_pipe_edge_styling.py -v
"""

import re
import pytest
from pipeviz import parse_size_mm, penwidth_from_mm, _pipe_edge_attrs, build_dot


# --- helpers ------------------------------------------------------------------

def _diag(components, connections, pipes):
    return {"components": components, "pipes": pipes, "connections": connections}


TANK = {"label": "Tank", "ports": ["in", "out"]}
PUMP = {"label": "Pump", "ports": ["in", "out"]}


# --- parse_size_mm ------------------------------------------------------------

def test_parse_size_mm_millimetres():
    assert parse_size_mm("25mm") == pytest.approx(25.0)


def test_parse_size_mm_millimetres_with_space():
    assert parse_size_mm("40 mm") == pytest.approx(40.0)


def test_parse_size_mm_inches_suffix():
    assert parse_size_mm("1in") == pytest.approx(25.4)


def test_parse_size_mm_inches_quote():
    assert parse_size_mm('1"') == pytest.approx(25.4)


def test_parse_size_mm_inches_word():
    assert parse_size_mm("1 inch") == pytest.approx(25.4)


def test_parse_size_mm_fractional_inches():
    assert parse_size_mm("1.5in") == pytest.approx(38.1)


def test_parse_size_mm_none():
    assert parse_size_mm(None) is None


def test_parse_size_mm_unrecognised():
    assert parse_size_mm("large") is None


# --- penwidth_from_mm ---------------------------------------------------------

def test_penwidth_from_mm_scaling():
    assert penwidth_from_mm(25.0) == pytest.approx(25.0 / 3.0)


def test_penwidth_from_mm_clamp_low():
    assert penwidth_from_mm(1.5) == pytest.approx(1.0)


def test_penwidth_from_mm_clamp_high():
    assert penwidth_from_mm(200.0) == pytest.approx(32.0)


# --- _pipe_edge_attrs ---------------------------------------------------------

def test_pipe_edge_attrs_explicit_colour():
    spec = {"label": "Hose", "colour": "BU"}
    attrs = _pipe_edge_attrs(spec)
    assert "#0066ff" in attrs  # BU resolved to hex


def test_pipe_edge_attrs_explicit_color_american():
    spec = {"label": "Hose", "color": "RD"}
    attrs = _pipe_edge_attrs(spec)
    assert "#ff0000" in attrs


def test_pipe_edge_attrs_colour_takes_priority_over_service():
    spec = {"label": "Hose", "colour": "RD", "service_rating": "potable"}
    attrs = _pipe_edge_attrs(spec)
    assert "#ff0000" in attrs
    assert "#0066ff" not in attrs  # potable blue should not appear


def test_pipe_edge_attrs_from_service_rating():
    spec = {"label": "Hose", "service_rating": "potable"}
    attrs = _pipe_edge_attrs(spec)
    assert "#a0dfff" in attrs  # LB = potable border colour


def test_pipe_edge_attrs_waste_service():
    spec = {"label": "Hose", "service_rating": "waste"}
    attrs = _pipe_edge_attrs(spec)
    assert "#ff0000" in attrs  # RD = waste border colour


def test_pipe_edge_attrs_no_colour_no_service():
    spec = {"label": "Hose"}
    attrs = _pipe_edge_attrs(spec)
    assert attrs == ""


def test_pipe_edge_attrs_includes_penwidth_for_sized_pipe():
    spec = {"label": "Hose", "size": "40mm", "colour": "BU"}
    attrs = _pipe_edge_attrs(spec)
    assert "penwidth" in attrs


def test_pipe_edge_attrs_no_penwidth_without_size():
    spec = {"label": "Hose", "colour": "BU"}
    attrs = _pipe_edge_attrs(spec)
    assert "penwidth" not in attrs


# --- build_dot integration ----------------------------------------------------

def test_build_dot_pipe_edge_has_colour():
    diag = _diag(
        {"tank": TANK, "pump": PUMP},
        connections=[["tank:out", "hose", "pump:in"]],
        pipes={"hose": {"label": "Hose", "colour": "BU", "size": "25mm"}},
    )
    dot = build_dot(diag, "test.yml")
    edges = re.findall(r'->.*?;', dot)
    pipe_edges = [e for e in edges if "color" in e]
    assert pipe_edges, "Expected at least one styled edge adjacent to pipe"


def test_build_dot_pipe_edge_has_penwidth():
    diag = _diag(
        {"tank": TANK, "pump": PUMP},
        connections=[["tank:out", "hose", "pump:in"]],
        pipes={"hose": {"label": "Hose", "colour": "BU", "size": "25mm"}},
    )
    dot = build_dot(diag, "test.yml")
    edges = re.findall(r'->.*?;', dot)
    pipe_edges = [e for e in edges if "penwidth" in e]
    assert pipe_edges, "Expected penwidth on pipe-adjacent edges"


def test_build_dot_both_flanking_edges_styled():
    diag = _diag(
        {"tank": TANK, "pump": PUMP},
        connections=[["tank:out", "hose", "pump:in"]],
        pipes={"hose": {"label": "Hose", "colour": "BU", "size": "25mm"}},
    )
    dot = build_dot(diag, "test.yml")
    edges = re.findall(r'->.*?;', dot)
    styled = [e for e in edges if "color" in e]
    assert len(styled) == 2, f"Expected both flanking edges styled, got {len(styled)}: {styled}"


def test_build_dot_component_to_component_edge_unstyled():
    diag = _diag(
        {"tank": TANK, "pump": PUMP},
        connections=[["tank:out", "pump:in"]],
        pipes={},
    )
    dot = build_dot(diag, "test.yml")
    edges = re.findall(r'->.*?;', dot)
    styled = [e for e in edges if "color=" in e]
    assert not styled, f"Expected no styled edges between components, got: {styled}"


def test_build_dot_service_rating_colours_edges():
    diag = _diag(
        {"tank": TANK, "pump": PUMP},
        connections=[["tank:out", "hose", "pump:in"]],
        pipes={"hose": {"label": "Potable Hose", "service_rating": "potable"}},
    )
    dot = build_dot(diag, "test.yml")
    assert "#a0dfff" in dot  # LB = potable border colour on edges
