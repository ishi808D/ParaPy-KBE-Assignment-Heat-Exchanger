# How it works

For this project you need: Docker Desktop running (install from https://www.docker.com/products/docker-desktop/), and a ParaPy license.

You can use this project in two ways:

1. Connect to a running container that already exposes a port.
2. (Recommended:) Set up a container first by running the provided `run_container.ps1` script. Do this via:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
.\run_container.ps1
```

## Required setup

- install uv yourself (if not done already)
- Add `parapy.lic` yourself.
- Log in to the ParaPy package index:

```powershell
uv auth login pypi.parapy.nl
```

- Run:
```powershell
uv init parapygui
uv sync
where python
```

- use ctrl+shift+P in vscode and click 'select interpreter'. Then choose for the option that corresponds to the just created uv installation
- run:
```powershell
python client.py --host localhost --port 50051 status
python client.py help
```
If the above outputs a list of commands, then the server is set up correctly.
- Start the ParaPy GUI using:
```powershell
cd parapygui
uv run python -m main # For normal GUI use
uv run python -m main --config inputs/requirements.json # For json-based use from the CLI
uv run python -m main --no-gui # for running the code in headless mode
```

## Working inside the container (for debugging)

Use the **Containers** extension in VS Code to see what is happening inside the container.
Attach VS Code to the running container to inspect the environment and runtime behavior directly.
