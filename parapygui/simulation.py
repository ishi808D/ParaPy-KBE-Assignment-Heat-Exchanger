"""
simulation.py
-------------
Bridge between the ParaPy GUI and the MTO/OpenFOAM gRPC server.

Maps to UML classes: **OpenFOAMSolverConnected**, **BaselineSimulation**,
**SimulationConfigSender**, **OptimizationHistory**

Uses the *existing* ``gyroid_service_pb2`` / ``_grpc`` stubs that are
already in the repo root.  The ``client.py`` CLI is used as a fallback
when the protobuf stubs are not importable (e.g. during development
without the container running).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


def _client_script() -> Path:
    """Return the path to ``client.py`` in the repo root."""
    return Path(__file__).resolve().parent.parent / "client.py"


def _run_client(host: str, port: int, *args: str,
                check: bool = True) -> subprocess.CompletedProcess:
    """Run a client.py sub-command and return the result."""
    cmd = [sys.executable, str(_client_script()),
           "--host", host, "--port", str(port), *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class SimulationConnector(Base):
    """Talks to the gRPC server that wraps the MTO topology optimiser.

    All heavy lifting is delegated to ``client.py`` via subprocess.
    This keeps the ParaPy side free of gRPC / protobuf dependencies
    (which only exist inside the container).

    Fire the action methods from the ParaPy property grid (right-click →
    "Evaluate / Fire").
    """

    host: str = Input("localhost")
    port: int = Input(50051)

    # ── status queries ───────────────────────────────────────────────

    @Attribute
    def server_status(self) -> str:
        """Current server state  (call ``status`` command)."""
        r = _run_client(self.host, self.port, "status", check=False)
        return r.stdout.strip() if r.returncode == 0 else r.stderr.strip()

    @Attribute
    def latest_metrics(self) -> str:
        """Latest optimisation metrics from the server."""
        r = _run_client(self.host, self.port, "latest", check=False)
        return r.stdout.strip() if r.returncode == 0 else "(no data)"

    @Attribute
    def optimisation_history(self) -> str:
        """Full history dump (large)."""
        r = _run_client(self.host, self.port, "history", check=False)
        return r.stdout if r.returncode == 0 else "(no data)"

    # ── config push ──────────────────────────────────────────────────

    def patch_config(self, kv_dict: dict) -> None:
        """Push a dict of key=value pairs to the gRPC config.

        Each entry becomes a ``client.py patch-config KEY=VALUE`` call.
        """
        assignments = [f"{k}={v}" for k, v in kv_dict.items()]
        _run_client(self.host, self.port, "patch-config", *assignments)

    def set_config_file(self, yaml_path: str) -> None:
        """Replace the entire server config from a YAML file."""
        _run_client(self.host, self.port, "set-config", yaml_path)

    # ── run control ──────────────────────────────────────────────────

    def start(self, extra_args: list[str] | None = None) -> str:
        """Start a simulation run on the server.

        Parameters
        ----------
        extra_args : list[str], optional
            Extra flags forwarded to the MTO wrapper, e.g.
            ``["--optimise"]`` to enable the optimisation loop.

        Returns
        -------
        str  —  server response message.
        """
        cmd = ["start"]
        if extra_args:
            cmd += ["--"] + extra_args
        r = _run_client(self.host, self.port, *cmd)
        return r.stdout.strip()

    def stop(self) -> str:
        """Stop the running simulation."""
        r = _run_client(self.host, self.port, "stop", check=False)
        return r.stdout.strip()

    # ── STL export / download ────────────────────────────────────────

    def trigger_stl_export(self, extra_args: list[str] | None = None) -> str:
        """Run ``gyroid_to_stl.py`` on the server."""
        cmd = ["stl-export"]
        if extra_args:
            cmd += ["--"] + extra_args
        r = _run_client(self.host, self.port, *cmd)
        return r.stdout.strip()

    def download_stl(self, which: str = "lattice",
                     out_dir: str = "outputs") -> str:
        """Download an STL file from the server.

        Parameters
        ----------
        which : ``"all"`` | ``"lattice"`` | ``"encap"`` | ``"surface"``
        out_dir : local directory to save the file.

        Returns
        -------
        str  —  path to the downloaded file.
        """
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        r = _run_client(self.host, self.port,
                        "download-stl", which, out_dir)
        # client.py prints "Done: <path>" on the last line
        for line in reversed(r.stdout.splitlines()):
            if line.startswith("Done:"):
                return line.split(":", 1)[1].strip()
        return str(Path(out_dir) / f"{which}.stl")

    def download_file(self, rel_path: str,
                      out_dir: str = "outputs") -> str:
        """Download any file from the server's ``app/`` directory."""
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        _run_client(self.host, self.port, "download", rel_path, out_dir)
        return str(Path(out_dir) / Path(rel_path).name)
