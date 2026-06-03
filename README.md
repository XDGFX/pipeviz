# pipeviz

A plumbing diagram tool that takes YAML descriptions of plumbing systems and produces Graphviz diagrams. Forked from [WireViz](https://github.com/wireviz/WireViz/) with a schema and rendering model designed for plumbing rather than electrical wiring.

## Installation

```bash
pip install pipeviz
```

Or install from source:

```bash
git clone https://github.com/xdgfx/pipeviz.git
cd pipeviz
pip install -e .
```

## Requirements

- Python 3.10+
- Graphviz (`dot` must be on your PATH)

## CLI Usage

```
pipeviz [options] <file...>
```

| Option | Short | Description |
|--------|-------|-------------|
| `--prepend FILE` | `-p` | YAML file to prepend before each diagram (repeatable) |
| `--format FORMAT` | `-f` | Output format: `svg`, `png`, `html`, `gv` (default: `svg`) |
| `--output-dir DIR` | `-o` | Directory for generated files |
| `--output-name NAME` | `-O` | Output filename without extension |
| `--version` | `-V` | Show version |

### Examples

```bash
# Generate SVG from a single file
pipeviz src/water_supply.yml

# Generate PNG with a shared component library prepended
pipeviz --prepend shared.yml --format png src/water_supply.yml

# Generate all diagrams into a specific directory
pipeviz --prepend shared.yml --output-dir out/ src/*.yml
```

## YAML Format

Each input file describes one diagram. See [SYNTAX.md](SYNTAX.md) for the full authoring reference.

```yaml
diagram:
  title: Cold Water Supply

components:
  tank:
    label: Fresh Water Tank
    ports: [outlet, drain, overflow]

  pump:
    label: 12V Demand Pump
    ports: [inlet, outlet]

pipes:
  pex_half:
    label: '1/2" PEX'
    service_rating: potable
    size: 15mm

connections:
  - - tank:outlet
    - pex_half
    - pump:inlet
```

## Prepend Files

A prepend file is a YAML file containing reusable `components` and `templates` that are merged before each diagram is processed. Use one to define a shared component library for your project:

```bash
pipeviz --prepend shared.yml src/water_supply.yml src/waste_system.yml
```

The prepend file has the same structure as a diagram file; its `components` and `templates` keys are merged into each diagram before parsing.

## Named Colours

All colour fields (`fillcolor`, `color`, `bgcolor`) accept 2-letter WireViz colour codes as well as hex strings and Graphviz named colours:

```yaml
components:
  my_valve:
    template: valve
    fillcolor: GN    # same as "#00ff00"
```

See [SYNTAX.md#named-colours](SYNTAX.md#named-colours) for the full palette.

## Python API

```python
from pipeviz import parse

parse("src/water_supply.yml", prepend_paths=["shared.yml"], format_type="svg", output_dir="out/")
```

```python
from pipeviz import build_dot

dot_source = build_dot(diagram_dict, file_path="example.yml")
```
