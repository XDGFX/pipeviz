"""
Slice A: Port normalisation to object format + portcount support
================================================================

AGENT TASK
----------
Modify `normalise_ports(component_spec)` in generate_all.py to return a
list of port *objects* (dicts with at least a "name" key) instead of a
list of plain strings.  Also add portcount-only support.

Functions to change in generate_all.py:
  - normalise_ports          — return type changes from list[str] to list[dict]
  - build_html_label         — iterate port["name"] instead of port
  - render_component_node    — (passes to build_html_label; may need no change)
  - validate_diagram         — port membership checks must use port["name"]

Do NOT change the public function signatures; only the return type of
normalise_ports changes.

Run these tests with:
  python -m pytest tests/test_slice_a_port_normalisation.py -v

All tests must be GREEN before handing off to the next agent.
"""

import pytest

from pipeviz import normalise_ports


def test_string_list_normalised_to_objects():
    result = normalise_ports({"ports": ["in", "out"]})
    assert result == [{"name": "in"}, {"name": "out"}]


def test_object_list_passed_through_intact():
    ports = [{"name": "in", "gender": "female"}, {"name": "out"}]
    assert normalise_ports({"ports": ports}) == ports


def test_integer_port_names_become_strings():
    assert normalise_ports({"ports": [1, 2]}) == [{"name": "1"}, {"name": "2"}]


def test_portcount_only_yields_1based_numeric_objects():
    assert normalise_ports({"portcount": 3}) == [
        {"name": "1"},
        {"name": "2"},
        {"name": "3"},
    ]


def test_ports_wins_when_both_present():
    spec = {"ports": ["a", "b"], "portcount": 2}
    assert normalise_ports(spec) == [{"name": "a"}, {"name": "b"}]


def test_empty_spec_returns_empty_list():
    assert normalise_ports({}) == []


def test_single_port_string_normalises():
    assert normalise_ports({"ports": ["inlet"]}) == [{"name": "inlet"}]


def test_portcount_one_yields_single_object():
    assert normalise_ports({"portcount": 1}) == [{"name": "1"}]


def test_optional_port_metadata_preserved():
    ports = [{"name": "out", "connection_size": '1/2"', "service_rating": "potable"}]
    assert normalise_ports({"ports": ports}) == ports
