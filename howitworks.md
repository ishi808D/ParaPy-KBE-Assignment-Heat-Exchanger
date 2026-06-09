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


## TODO
Create a ParaPy GUI using the parapy tools, also use wxformbuilder (see https://parapy.nl/docs/parapy/latest/tutorials/gui_widgets.html?highlight=wxformbuilder) and (https://ai.parapy.nl). Let the GUI follow the steps described in the KBE Proposal Document. The GUI should interact with the optimiser using the python commands described by `python client.py help`. Also use https://parapy.nl/docs/parapy/latest/examples/examples_tree/exchange/stl_reader.html#exchange-stl-reader-py to show stl inside the ParaPy GUI.