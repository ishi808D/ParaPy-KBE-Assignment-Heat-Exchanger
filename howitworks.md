# How it works

You can use this project in two ways:

1. Connect to a running container that already exposes a port.
2. Set up a container first by running the provided `run_container.ps1` script. Do this via:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\run_container.ps1
```

## Required setup

- install uv yourself (if not done already)
- Add `parapy.lic` yourself.
- Log in to the ParaPy package index:

```bash
uv auth login pypi.parapy.nl
```

- Run:
```bash
uv init parapygui
uv sync
where python
```

- use ctrl+shift+P in vscode and click 'select interpreter'. Then choose for the option that corresponds to the just created uv installation
- run:
```bash
python client.py --host localhost --port 50051 status
python client.py help
```

## Working inside the container

Use the **Containers** extension in VS Code to see what is happening inside the container.
Attach VS Code to the running container to inspect the environment and runtime behavior directly.

## Export pipeline

The app exports two sibling artifacts from the same prepared gyroid geometry:

1. STL comes from the STL export path and is the mesh artifact used for preview and downstream manufacturing checks.
2. STEP comes from the quad-mesh path followed by the NURBS converter, so it depends on quad OBJ generation rather than on STL.

That means STL and STEP are parallel outputs, not a conversion chain from STL to STEP.

## Inlet / outlet geometry

The wizard now separates two concepts that the repo previously mixed together:

1. Container flow patches, which are the inlet/outlet windows and their origins/sizes in mm.
2. Physical ParaPy port geometry, which is the inlet/outlet diameter, tube wall, and tube length.

The container remains the source of truth for the flow-patch configuration, while the local ParaPy model remains the source of truth for the cylindrical port CAD.


## TODO
Create a ParaPy GUI using the parapy tools, also use wxformbuilder (see https://parapy.nl/docs/parapy/latest/tutorials/gui_widgets.html?highlight=wxformbuilder) and (https://ai.parapy.nl). Let the GUI follow the steps described in the KBE Proposal Document. The GUI should interact with the optimiser using the python commands described by `python client.py help`. Also use https://parapy.nl/docs/parapy/latest/examples/examples_tree/exchange/stl_reader.html#exchange-stl-reader-py to show stl inside the ParaPy GUI.


## Run Parapy
uv run python -m parapygui.main
=======