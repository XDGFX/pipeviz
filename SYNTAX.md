# Diagram Authoring Reference

How to write a diagram file for pipeviz.

---

## File Skeleton

```yaml
diagram:
  title: My System          # optional — defaults to filename
  rankdir: LR               # optional — LR (left-to-right, default) or TB (top-to-bottom)

components:
  my_component:
    label: Display Label    # required
    ports: [in, out]        # required — OR use portcount (see below)
    ref: shared_key         # optional — inherit label + ports from a prepend file
    template: valve         # optional — apply a visual style without inheriting ports
    # optional metadata (not validated, shown in tooltip/BOM):
    manufacturer: ACME
    model: AV-100
    description: Manual isolation valve

pipes:
  half_inch_pex:
    label: '1/2" PEX'       # required
    # optional pipe metadata:
    material: PEX-B
    size: '1/2"'
    colour: BU                 # explicit edge colour (WireViz 2-letter code or hex); overrides service_rating
    service_rating: potable    # potable · waste · vent · hot — sets edge colour automatically
    description: Cold supply run

connections:
  - - component_a:port      # direct connection
    - component_b:port
  - - component_a:port      # pipe-mediated connection
    - pipe_type
    - component_b:port
```

---

## Components

### Ports

Declare ports as a list of strings:

```yaml
components:
  pump:
    label: Demand Pump
    ports: [inlet, outlet]
```

Or use `portcount` when ports will be referenced by number:

```yaml
  manifold:
    label: Distribution Manifold
    portcount: 4            # ports referenced as manifold:1, manifold:2, manifold:3, manifold:4
```

`ports` and `portcount` may coexist; `portcount` must equal the length of `ports` when both are present.

### Detailed port objects

When you need port-level metadata, use object form instead of a string list:

```yaml
  my_valve:
    label: Isolation Valve
    ports:
      - name: inlet
        connection_size: '1/2"'
        gender: female
        service_rating: potable
      - name: outlet
        connection_size: '1/2"'
        gender: male
```

### Using a prepend file (`ref:`)

If the project has a prepend file, `ref:` copies a component definition (label + ports) from it:

```yaml
components:
  main_pump:
    ref: pump_12v           # inherits label and ports from the prepend file

  kitchen_sink:
    ref: sink_faucet
    label: Kitchen Sink     # overrides the shared label
```

### Using templates (`template:`)

`template:` applies a visual style but does **not** inherit ports — you must declare them yourself:

```yaml
  mixing_valve:
    template: valve
    label: Thermostatic Mixing Valve
    ports: [cold_in, hot_in, mixed_out, sensor]
```

---

## Pipes

Declare every pipe type under `pipes:` before using it in `connections`:

```yaml
pipes:
  pex_half:
    label: '1/2" PEX'
  pex_three_quarter:
    label: '3/4" PEX'
  copper_half:
    label: '1/2" Copper'
```

Each use of a pipe name in a `connections` chain creates a fresh unnamed pipe run — the same name can appear in multiple chains without conflict.

### Pipe edge styling

Edges connecting a pipe node to a component are styled to visually represent the hose:

- **`colour`** (or `color`) — explicit edge colour as a WireViz 2-letter code (e.g. `BU`) or hex string. Takes priority over `service_rating`.
- **`service_rating`** — if no explicit colour is set, the border colour for that service is used on edges.
- **`size`** — drives `penwidth` on edges proportional to the pipe diameter. Accepts `mm` or inch units (`in`, `"`, `inch`).

Setting `service_rating` on a pipe also applies a fill and border colour to the pipe node itself. The built-in services are `potable`, `waste`, `vent`, and `hot`. Custom service ratings can be added by extending `SERVICE_COLORS` in `pv_colors.py`.

---

## Connections

### Token syntax

| Token | Meaning |
|-------|---------|
| `component` | Component, first port (default) |
| `component:port` | Component, named port |
| `component:3` | Component, third port (numeric, 1-based) |
| `component.name` | Named instance — same identity reused across chains |
| `component.name:port` | Named instance, specific port |
| `component.:port` | Unnamed instance — fresh occurrence each time |
| `pipe_type` | Creates a unique unnamed pipe run |
| `pipe_type^` | Reversed pipe run — flips direction of subsequent connections. Adds `constraint=false` to reversed edges. |

### Rules

- Every chain must have **at least 2 tokens**.
- **Pipe-to-pipe adjacency is invalid** — always separate pipes with a component token.
- Each `pipe_type` token in a chain is a fresh run; the same type can appear multiple times.

### Examples

```yaml
connections:
  # Direct connection (no pipe)
  - - pump:outlet
    - filter:inlet

  # Pipe-mediated connection
  - - pump:outlet
    - pex_half
    - filter:inlet

  # Multi-hop chain (two pipes, one component in the middle)
  - - tank:outlet
    - pex_three_quarter
    - pump:inlet

  - - pump:outlet
    - pex_half
    - manifold:inlet

  # Omitted port defaults to first port
  - - pump
    - filter

  # Named instances — two sinks sharing the same manifold branch identity
  - - manifold:zone_1
    - pex_half
    - sink.kitchen:cold_in

  - - manifold:zone_2
    - pex_half
    - sink.bathroom:cold_in

  # Unnamed instance — each occurrence is a distinct component; tees will not connect to each other!
  - - supply
    - pex_half
    - tee.

  - - tee.
    - pex_half
    - sink_a

  - - tee.
    - pex_half
    - sink_b
```

---

## Named Colours

Any field that accepts a colour value (`fillcolor`, `color`, `bgcolor`) accepts
either a hex string or a 2-letter WireViz style colour code:

```yaml
components:
  my_valve:
    template: valve
    fillcolor: GN    # same as "#00ff00"
    color: OL        # same as "#708000"

diagram:
  bgcolor: IV        # ivory background
```

Full palette:

| Code | Hex | Name |
|------|-----|------|
| `BK` | `#000000` | black |
| `WH` | `#ffffff` | white |
| `GY` | `#999999` | grey |
| `PK` | `#ff66cc` | pink |
| `RD` | `#ff0000` | red |
| `OG` | `#ff8000` | orange |
| `YE` | `#ffff00` | yellow |
| `OL` | `#708000` | olive green |
| `GN` | `#00ff00` | green |
| `TQ` | `#00ffff` | turquoise |
| `LB` | `#a0dfff` | light blue |
| `BU` | `#0066ff` | blue |
| `VT` | `#8000ff` | violet |
| `BN` | `#895956` | brown |
| `BG` | `#ceb673` | beige |
| `IV` | `#f5f0d0` | ivory |
| `SL` | `#708090` | slate |
| `CU` | `#d6775e` | copper |
| `SN` | `#aaaaaa` | tin |
| `SR` | `#84878c` | silver |
| `GD` | `#ffcf80` | gold |

Codes are case-insensitive. Hex strings and Graphviz named colours (e.g. `white`, `transparent`) pass through unchanged.

---

## Visual Templates

Used with `template:` to control node appearance.

| Template | Shape | Fill colour |
|----------|-------|-------------|
| `tank` | 3D box | Blue |
| `pump` | Box | Orange |
| `filter` | Box | Light grey |
| `valve` | Box | Green |
| `heater` | Box | Red |
| `fixture` | Box | Sky blue |
| `manifold` | Box | Amber |
| `trap` | Box | Purple |
| `offpage` | Oval | Off-white |
| `vent` | Oval | Lime |

---

## Minimal Working Example

```yaml
diagram:
  title: Cold Water Supply

components:
  supply_in:
    label: Shore Water
    ports: [in]

  pump:
    label: 12V Demand Pump
    ports: [inlet, outlet]

  sediment:
    label: Sediment Filter
    ports: [inlet, outlet, drain]

  tap:
    label: Kitchen Tap
    ports: [cold_in, hot_in, drain]

pipes:
  pex_half:
    label: '1/2" PEX'

connections:
  - - supply_in:in
    - pex_half
    - pump:inlet

  - - pump:outlet
    - pex_half
    - sediment:inlet

  - - sediment:outlet
    - pex_half
    - tap:cold_in
```
