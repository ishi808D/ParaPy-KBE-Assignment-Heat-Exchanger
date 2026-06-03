# parapygui — Bio-Inspired Heat Exchanger KBE App

**TU Delft AE4204 Knowledge Based Engineering — Team 16** (Desai & Huirne)

## Quick start

```bash
# From the repo root (where client.py lives)
cd parapygui

# First-time setup
uv sync

# Launch the GUI
python -m parapygui.main

# Or with a custom config
python -m parapygui.main --config inputs/requirements.json

# Print design summary without GUI (CI / testing)
python -m parapygui.main --no-gui
```

## Module overview

| File | UML class(es) | Purpose |
|---|---|---|
| `fluid.py` | FluidElement | Coolant thermophysical properties |
| `lattice.py` | LatticeElement, TPMSFrequencyField, LatticeFormulation | TPMS wavenumber fields + solid material |
| `encapsulation.py` | Encapsulation, InletOutletSpecification | 3-D CAD geometry (the only visual part) |
| `environment.py` | HeatExchangerEnvironment | Boundary conditions (velocity, temperature, pressure) |
| `objectives.py` | Objectives, ManufacturingConstraintSet | Optimiser mode + DfAM constraints |
| `solidity.py` | SemiEmpirical | Femmer et al. (2023) correlations |
| `simulation.py` | SimulationConnector | gRPC bridge to MTO/OpenFOAM container |
| `geometry_export.py` | GeometryExportService | STL reader, STL→STEP reconstruction, STEP writer |
| `loader.py` | Loader | JSON + Excel input file parsing |
| `validators.py` | — | Cross-parameter validation |
| `heat_exchanger.py` | HeatExchanger | **Root class** — assembles everything |
| `main.py` | — | Entry point, CLI argument parser |

## Workflow

1. Edit encapsulation geometry + flow conditions in the property grid
2. Fire `start_baseline()` → single OpenFOAM run via gRPC
3. Fire `start_optimisation()` → full topology optimisation loop
4. Fire `export_stl()` → download optimised lattice from server
5. Fire `export_step()` → write encapsulation shell to STEP
