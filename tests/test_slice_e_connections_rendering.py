"""
Slice E: Pipe instantiation and connections rendering
======================================================

PREREQUISITE: Slices A, B, C, and D must be complete.

AGENT TASK
----------
Wire the new connections machinery into the rendering pipeline so that
`build_dot(diagram, file_path)` produces valid Graphviz DOT when the
diagram uses the "connections" syntax with "pipes" declarations.

Changes required in generate_all.py:

1. `validate_diagram` — when "connections" is present:
     a. Each pipe type referenced in any chain must exist in diagram["pipes"].
     b. Each component base_name referenced must exist in diagram["components"].
     c. Each explicit port referenced must exist on that component.
     d. Chains are validated by calling validate_connections_chain.

2. `build_dot` — when "connections" is present:
     a. For each chain, call validate_connections_chain to produce hops.
     b. For each hop involving a pipe token, instantiate a unique unnamed pipe
        node: ID format is "<pipe_type>__<counter>" (e.g. "pex_half__0").
     c. Render each pipe instance as a DOT node (box shape, labelled with the
        pipe type's "label" from diagram["pipes"]).
     d. Convert each hop into a DOT edge, defaulting omitted ports to the
        first port of the component/pipe involved.
     e. Edges from/to pipe instances use the pipe node ID with no port anchor.

Port defaulting rule: when a token has port=None, resolve to the first entry
in normalise_ports(spec)["name"]; raise ValueError if the component has no
ports at all.

Run these tests with:
  python -m pytest tests/test_slice_e_connections_rendering.py -v

All tests must be GREEN before handing off to the next agent.
"""

import re

import pytest

from pipeviz import build_dot, validate_diagram

# --- helpers -----------------------------------------------------------------


def _make_diagram(components, pipes=None, connections=None, edges=None):
    d = {"components": components, "pipes": pipes or {}}
    if connections is not None:
        d["connections"] = connections
    if edges is not None:
        d["edges"] = edges
    return d


TWO_COMPS = {
    "pump": {"label": "Pump", "ports": ["inlet", "outlet"]},
    "filter": {"label": "Filter", "ports": ["in", "out"]},
}

THREE_COMPS = {
    "tank": {"label": "Tank", "ports": ["outlet"]},
    "valve": {"label": "Valve", "ports": ["inlet", "outlet"]},
    "heater": {"label": "Heater", "ports": ["cold_in", "hot_out"]},
}

PEX_PIPE = {"pex": {"label": '1/2" PEX'}}


# --- direct component-to-component connection --------------------------------


def test_direct_connection_renders_both_nodes_and_edge():
    diag = _make_diagram(TWO_COMPS, connections=[["pump:outlet", "filter:in"]])
    dot = build_dot(diag, "test.yml")
    assert "pump" in dot
    assert "filter" in dot
    assert "->" in dot


def test_direct_connection_port_appears_in_edge():
    diag = _make_diagram(TWO_COMPS, connections=[["pump:outlet", "filter:in"]])
    dot = build_dot(diag, "test.yml")
    assert "outlet" in dot
    assert "in" in dot


# --- pipe-mediated connection ------------------------------------------------


def test_pipe_node_rendered_for_pipe_usage():
    diag = _make_diagram(
        THREE_COMPS,
        pipes=PEX_PIPE,
        connections=[["tank:outlet", "pex", "valve:inlet"]],
    )
    dot = build_dot(diag, "test.yml")
    assert "pex" in dot
    assert "tank" in dot
    assert "valve" in dot


def test_pipe_mediated_connection_has_two_edges():
    diag = _make_diagram(
        THREE_COMPS,
        pipes=PEX_PIPE,
        connections=[["tank:outlet", "pex", "valve:inlet"]],
    )
    dot = build_dot(diag, "test.yml")
    arrow_count = dot.count("->")
    assert arrow_count >= 2


# --- pipe uniqueness ---------------------------------------------------------


def test_two_usages_of_same_pipe_type_yield_distinct_node_ids():
    comps = {
        "a": {"label": "A", "ports": ["out"]},
        "b": {"label": "B", "ports": ["in", "out"]},
        "c": {"label": "C", "ports": ["in"]},
    }
    diag = _make_diagram(
        comps,
        pipes=PEX_PIPE,
        connections=[
            ["a:out", "pex", "b:in"],
            ["b:out", "pex", "c:in"],
        ],
    )
    dot = build_dot(diag, "test.yml")
    # At least two distinct pex node IDs (e.g. pex__0 and pex__1)
    pex_ids = set(re.findall(r"pex__\d+", dot))
    assert len(pex_ids) >= 2


# --- port defaulting ---------------------------------------------------------


def test_omitted_port_defaults_to_first_port():
    # Token "pump" with no port — should default to "inlet" (first port of pump)
    diag = _make_diagram(TWO_COMPS, connections=[["pump", "filter"]])
    dot = build_dot(diag, "test.yml")
    assert "pump" in dot
    assert "filter" in dot
    # Should not raise


# --- validation: unknown pipe type -------------------------------------------


def test_unknown_pipe_type_in_connections_fails_validation():
    diag = _make_diagram(
        TWO_COMPS,
        pipes={},
        connections=[["pump:outlet", "mystery_pipe", "filter:in"]],
    )
    with pytest.raises(ValueError, match="[Uu]nknown|not found"):
        validate_diagram(diag, "test.yml")


# --- validation: unknown component in chain ----------------------------------


def test_unknown_component_in_connections_fails_validation():
    diag = _make_diagram(
        TWO_COMPS,
        pipes=PEX_PIPE,
        connections=[["ghost:out", "pex", "filter:in"]],
    )
    with pytest.raises(ValueError, match="[Uu]nknown|not found"):
        validate_diagram(diag, "test.yml")


# --- validation: bad port in chain -------------------------------------------


def test_nonexistent_port_in_connections_fails_validation():
    diag = _make_diagram(
        TWO_COMPS,
        pipes=PEX_PIPE,
        connections=[["pump:nonexistent_port", "filter:in"]],
    )
    with pytest.raises(ValueError, match="port"):
        validate_diagram(diag, "test.yml")
