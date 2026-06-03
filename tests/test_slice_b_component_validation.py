"""
Slice B: Component validation rules
====================================

PREREQUISITE: Slice A must be complete (normalise_ports returns list[dict]).

AGENT TASK
----------
Extend `validate_diagram(diagram, file_path)` in generate_all.py to enforce
the new component schema rules from ADR 0001 and CONTEXT.md:

  1. Every component must have a "label".
  2. Every component must have at least one of "ports" or "portcount".
  3. When both "ports" and "portcount" are present, portcount must equal
     len(ports); raise ValueError if they disagree.
  4. A diagram must define a non-empty "connections" list.

Do NOT change the function signature.

Run these tests with:
  cd /Users/cal/git/truck_2025_plumbing
  python -m pytest tests/test_slice_b_component_validation.py -v

All tests must be GREEN before handing off to the next agent.
"""

import pytest
from pipeviz import validate_diagram


# --- helpers -----------------------------------------------------------------

def _diagram(components, connections=None):
    d = {"components": components, "pipes": {}}
    if connections is not None:
        d["connections"] = connections
    return d


def _two_port_components():
    return {
        "tank": {"label": "Tank", "ports": ["outlet"]},
        "pump": {"label": "Pump", "ports": ["inlet", "outlet"]},
    }


# --- label requirement -------------------------------------------------------

def test_component_missing_label_raises():
    diag = _diagram(
        {"tank": {"ports": ["in", "out"]}},
        connections=[["tank:in", "tank:out"]],
    )
    with pytest.raises(ValueError, match="label"):
        validate_diagram(diag, "test.yml")


def test_empty_label_raises():
    diag = _diagram(
        {"tank": {"label": "", "ports": ["in"]}},
        connections=[["tank:in", "tank:in"]],
    )
    with pytest.raises(ValueError, match="label"):
        validate_diagram(diag, "test.yml")


# --- ports / portcount requirement -------------------------------------------

def test_component_with_neither_ports_nor_portcount_raises():
    diag = _diagram(
        {"tank": {"label": "Tank"}},
        connections=[["tank", "tank"]],
    )
    with pytest.raises(ValueError, match="ports|portcount"):
        validate_diagram(diag, "test.yml")


def test_portcount_mismatch_with_ports_raises():
    diag = _diagram(
        {"tank": {"label": "Tank", "ports": ["in", "out"], "portcount": 3}},
        connections=[["tank:in", "tank:out"]],
    )
    with pytest.raises(ValueError, match="portcount"):
        validate_diagram(diag, "test.yml")


def test_portcount_matching_ports_passes():
    diag = _diagram(
        {
            "a": {"label": "A", "ports": ["in", "out"], "portcount": 2},
            "b": {"label": "B", "ports": ["in"]},
        },
        connections=[["a:out", "b:in"]],
    )
    validate_diagram(diag, "test.yml")  # must not raise


def test_portcount_only_component_passes():
    diag = _diagram(
        {
            "a": {"label": "A", "portcount": 2},
            "b": {"label": "B", "portcount": 2},
        },
        connections=[["a:1", "b:1"]],
    )
    validate_diagram(diag, "test.yml")  # must not raise


# --- connections requirement -------------------------------------------------

def test_diagram_with_connections_passes():
    diag = _diagram(_two_port_components(), connections=[["tank:outlet", "pump:inlet"]])
    validate_diagram(diag, "test.yml")  # must not raise


def test_diagram_without_connections_raises():
    diag = _diagram(_two_port_components())
    with pytest.raises(ValueError):
        validate_diagram(diag, "test.yml")


def test_diagram_with_empty_connections_raises():
    diag = _diagram(_two_port_components(), connections=[])
    with pytest.raises(ValueError):
        validate_diagram(diag, "test.yml")
