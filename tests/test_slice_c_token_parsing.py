"""
Slice C: Connection token parsing
==================================

PREREQUISITE: Slices A and B must be complete.

AGENT TASK
----------
Add a new public function to generate_all.py:

    parse_connection_token(token: str) -> dict

Return value shape:
    {
        "base_name": str,       # component or pipe type name
        "instance":  str|None,  # None → base ref, "" → unnamed one-time, "x" → named "x"
        "port":      str|None,  # explicit port name/number, or None if omitted
    }

Token grammar (from ADR 0001):
    token       = name [ instance_suffix ] [ ":" port ]
    name        = identifier
    instance_suffix = "." [ identifier ]   # "." alone = unnamed; ".foo" = named "foo"
    port        = identifier | integer

Rules:
  - At most ONE port per token; list/range syntax is invalid → raise ValueError.
  - Tokens that reference a pipe type (resolved later) follow the same grammar;
    this function is purely syntactic and does not consult component/pipe dicts.

Run these tests with:
  python -m pytest tests/test_slice_c_token_parsing.py -v

All tests must be GREEN before handing off to the next agent.
"""

import pytest

from pipeviz import parse_connection_token

# --- base component reference ------------------------------------------------


def test_bare_name_is_base_ref():
    t = parse_connection_token("tank")
    assert t["base_name"] == "tank"
    assert t["instance"] is None
    assert t["port"] is None


def test_base_ref_with_named_port():
    t = parse_connection_token("tank:cold_in")
    assert t["base_name"] == "tank"
    assert t["instance"] is None
    assert t["port"] == "cold_in"


def test_base_ref_with_numeric_port():
    t = parse_connection_token("fitting:1")
    assert t["base_name"] == "fitting"
    assert t["instance"] is None
    assert t["port"] == "1"


# --- named instance ----------------------------------------------------------


def test_named_instance_no_port():
    t = parse_connection_token("tank.a")
    assert t["base_name"] == "tank"
    assert t["instance"] == "a"
    assert t["port"] is None


def test_named_instance_with_port():
    t = parse_connection_token("tank.a:cold_in")
    assert t["base_name"] == "tank"
    assert t["instance"] == "a"
    assert t["port"] == "cold_in"


def test_named_instance_multi_char():
    t = parse_connection_token("pump.primary:outlet")
    assert t["base_name"] == "pump"
    assert t["instance"] == "primary"
    assert t["port"] == "outlet"


# --- unnamed one-time instance -----------------------------------------------


def test_unnamed_instance_bare():
    t = parse_connection_token("tank.")
    assert t["base_name"] == "tank"
    assert t["instance"] == ""
    assert t["port"] is None


def test_unnamed_instance_with_port():
    t = parse_connection_token("tank.:out")
    assert t["base_name"] == "tank"
    assert t["instance"] == ""
    assert t["port"] == "out"


# --- multi-port token is invalid ---------------------------------------------


def test_list_port_syntax_raises():
    with pytest.raises(ValueError, match="[Mm]ulti.port|single port|at most one"):
        parse_connection_token("tank:[in,out]")


def test_range_port_syntax_raises():
    with pytest.raises(ValueError, match="[Mm]ulti.port|single port|at most one"):
        parse_connection_token("connector:1-3")


# --- edge cases --------------------------------------------------------------


def test_empty_string_raises():
    with pytest.raises(ValueError):
        parse_connection_token("")


def test_pipe_type_bare_name_parses_as_base_ref():
    # Pipes have no instance syntax in authored YAML; bare name is valid.
    t = parse_connection_token("pex_half_inch")
    assert t["base_name"] == "pex_half_inch"
    assert t["instance"] is None
    assert t["port"] is None
