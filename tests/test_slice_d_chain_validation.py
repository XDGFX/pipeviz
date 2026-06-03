"""
Slice D: Connection chain validation
======================================

PREREQUISITE: Slices A, B, and C must be complete.

AGENT TASK
----------
Add a new public function to generate_all.py:

    validate_connections_chain(
        chain:           list[str],
        component_names: set[str],
        pipe_names:      set[str],
    ) -> list[dict]

The function validates one `connections` chain and returns the hops it
produces.  Each hop is a dict:

    {
        "from": <parsed token dict from parse_connection_token>,
        "to":   <parsed token dict from parse_connection_token>,
        "from_kind": "component" | "pipe",
        "to_kind":   "component" | "pipe",
    }

A chain of N tokens produces N-1 hops.

Validation rules (ADR 0001):
  1. Chain must contain at least two tokens.
  2. Every token's base_name must exist in component_names OR pipe_names; raise
     ValueError if unknown.
  3. Pipe-to-pipe adjacent hops are invalid → raise ValueError.
  4. Component-to-component and component-to-pipe (either direction) are valid.

Port resolution (default to first port) is NOT done here; that is deferred
to the rendering stage in Slice E.

Run these tests with:
  python -m pytest tests/test_slice_d_chain_validation.py -v

All tests must be GREEN before handing off to the next agent.
"""

import pytest

from pipeviz import validate_connections_chain

COMPONENTS = {"tank", "pump", "valve", "filter", "heater"}
PIPES = {"pex_half", "pex_quarter", "copper_half"}


# --- minimum length ----------------------------------------------------------


def test_single_token_chain_raises():
    with pytest.raises(ValueError, match="[Aa]t least two|[Mm]inimum"):
        validate_connections_chain(["tank"], COMPONENTS, PIPES)


def test_empty_chain_raises():
    with pytest.raises(ValueError, match="[Aa]t least two|[Mm]inimum|[Ee]mpty"):
        validate_connections_chain([], COMPONENTS, PIPES)


# --- valid hop types ---------------------------------------------------------


def test_direct_component_to_component_is_valid():
    hops = validate_connections_chain(["pump:outlet", "filter:in"], COMPONENTS, PIPES)
    assert len(hops) == 1
    assert hops[0]["from"]["base_name"] == "pump"
    assert hops[0]["to"]["base_name"] == "filter"
    assert hops[0]["from_kind"] == "component"
    assert hops[0]["to_kind"] == "component"


def test_component_pipe_component_chain_is_valid():
    hops = validate_connections_chain(
        ["tank:outlet", "pex_half", "valve:inlet"], COMPONENTS, PIPES
    )
    assert len(hops) == 2
    assert hops[0]["from_kind"] == "component"
    assert hops[0]["to_kind"] == "pipe"
    assert hops[1]["from_kind"] == "pipe"
    assert hops[1]["to_kind"] == "component"


def test_five_token_chain_yields_four_hops():
    hops = validate_connections_chain(
        ["tank:outlet", "pex_half", "valve:mid", "pex_quarter", "heater:inlet"],
        COMPONENTS,
        PIPES,
    )
    assert len(hops) == 4


def test_chain_starting_with_pipe_is_valid():
    hops = validate_connections_chain(["pex_half", "valve:inlet"], COMPONENTS, PIPES)
    assert hops[0]["from_kind"] == "pipe"
    assert hops[0]["to_kind"] == "component"


# --- invalid hop types -------------------------------------------------------


def test_pipe_to_pipe_hop_raises():
    with pytest.raises(ValueError, match="[Pp]ipe.to.[Pp]ipe|[Aa]djacent pipe"):
        validate_connections_chain(["pex_half", "copper_half"], COMPONENTS, PIPES)


def test_pipe_to_pipe_in_longer_chain_raises():
    with pytest.raises(ValueError, match="[Pp]ipe.to.[Pp]ipe|[Aa]djacent pipe"):
        validate_connections_chain(
            ["tank:out", "pex_half", "pex_quarter", "valve:in"],
            COMPONENTS,
            PIPES,
        )


# --- unknown references ------------------------------------------------------


def test_unknown_component_raises():
    with pytest.raises(ValueError, match="[Uu]nknown|not found"):
        validate_connections_chain(["mystery_comp:out", "valve:in"], COMPONENTS, PIPES)


def test_unknown_pipe_raises():
    with pytest.raises(ValueError, match="[Uu]nknown|not found"):
        validate_connections_chain(
            ["tank:out", "mystery_pipe", "valve:in"], COMPONENTS, PIPES
        )


# --- named and unnamed instances still resolve to valid components -----------


def test_named_instance_resolves_correctly():
    hops = validate_connections_chain(
        ["tank.a:out", "pump.primary:inlet"], COMPONENTS, PIPES
    )
    assert hops[0]["from"]["base_name"] == "tank"
    assert hops[0]["from"]["instance"] == "a"
    assert hops[0]["from_kind"] == "component"


def test_unnamed_instance_resolves_correctly():
    hops = validate_connections_chain(["tank.:out", "valve:in"], COMPONENTS, PIPES)
    assert hops[0]["from"]["instance"] == ""
    assert hops[0]["from_kind"] == "component"
