"""
webapp.py
---------
FastAPI web server for the Bio-Inspired Heat Exchanger KBE application.

Exposes the computational core (gyroid generation, sizing, manufacturability,
gRPC simulation control) as a REST API consumed by the browser frontend.

Run:
    uvicorn parapygui.webapp:app --host 0.0.0.0 --port 8000 --reload

Then open http://localhost:8000 in any browser.

Architecture
~~~~~~~~~~~~
    Browser  ←→  FastAPI (port 8000)  ←→  parapygui computational classes
                                      ←→  MTO gRPC server (port 50051, Docker)

The heavy lifting (gyroid mesh generation, manufacturability, semi-empirical
sizing) is done by the same Python classes used by the ParaPy GUI — they
all inherit from ``parapy.core.Base`` which works without a display.
"""

from __future__ import annotations

import io
import json
import struct
from pathlib import Path
from typing import Any

from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import (FileResponse, JSONResponse,
                               StreamingResponse, HTMLResponse)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ── app ──────────────────────────────────────────────────────────────────────

app = FastAPI(title="Bio-Inspired Heat Exchanger KBE", version="0.1.0")

_STATIC = Path(__file__).parent / "static"
if _STATIC.exists():
    app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")

# ── request / response models ─────────────────────────────────────────────

class DesignParams(BaseModel):
    # Geometry
    enc_length:          float = 0.10
    enc_width:           float = 0.05
    enc_height:          float = 0.05
    enc_wall_thickness:  float = 0.002
    # Lattice
    initial_wavenumber:  float = 628.0
    iso_level:           float = 0.30
    resolution:          int   = 50
    # Flow
    inflow_velocity:     float = 1.0
    inflow_temperature:  float = 350.0
    exterior_temperature:float = 293.15
    outlet_pressure:     float = 101325.0
    # Objectives
    optimizer_mode:      str   = "minimize_outlet_temperature"
    target_nusselt:      float = 10.0
    operating_reynolds:  float = 1000.0
    # DfAM
    min_feature_size:    float = 2e-4
    max_overhang_angle:  float = 45.0
    # gRPC
    grpc_host:           str   = "localhost"
    grpc_port:           int   = 50051


class SimStartParams(BaseModel):
    # Full design params so the server runs the design the user configured
    design:    DesignParams = DesignParams()
    optimise:  bool = False


def _push_design_config(p: DesignParams) -> None:
    """Push the current design parameters to the gRPC server.

    Builds the dot-notation config dict the MTO server expects and sends it
    via ``patch-config`` so the next ``start`` runs the user's design rather
    than whatever was configured before.
    """
    from parapygui.simulation import SimulationConnector
    from math import pi
    sim = SimulationConnector(host=p.grpc_host, port=p.grpc_port)
    il, iw, ih = _interior(p)
    cfg = {
        # geometry
        "geometry.length":         p.enc_length,
        "geometry.width":          p.enc_width,
        "geometry.height":         p.enc_height,
        "geometry.wall_thickness": p.enc_wall_thickness,
        # boundary conditions
        "run.inflow_velocity":      p.inflow_velocity,
        "run.inflow_temperature":   p.inflow_temperature,
        "run.outlet_pressure":      p.outlet_pressure,
        "run.exterior_temperature": p.exterior_temperature,
        # lattice initial state
        "lattice.wavenumber":      p.initial_wavenumber,
        "lattice.iso_level":       p.iso_level,
        # optimiser
        "optimization.mode": ("heat"
                              if p.optimizer_mode == "minimize_outlet_temperature"
                              else "pressure"),
        "optimization.target_nusselt":     p.target_nusselt,
        "optimization.min_wall_thickness": p.min_feature_size,
        "optimization.max_overhang_angle": p.max_overhang_angle,
    }
    sim.patch_config(cfg)


# ── helpers ──────────────────────────────────────────────────────────────────

def _interior(p: DesignParams):
    t = p.enc_wall_thickness
    return (p.enc_length - 2*t,
            p.enc_width  - 2*t,
            p.enc_height - 2*t)


def _hydraulic_diam(p: DesignParams) -> float:
    _, w, h = _interior(p)
    return 4 * w * h / (2 * (w + h))


def _build_fluid():
    from parapygui.fluid import FluidElement
    return FluidElement()


def _build_sizing(p: DesignParams, fluid, dh: float, sim_re: float):
    from parapygui.solidity import SemiEmpirical
    return SemiEmpirical(
        hydraulic_diameter=dh,
        inflow_velocity=p.inflow_velocity,
        kinematic_viscosity=fluid.kinematic_viscosity,
        fluid_conductivity=fluid.conductivity,
        prandtl_number=fluid.prandtl_number,
        target_nusselt=p.target_nusselt,
        operating_re=p.operating_reynolds,
        simulation_re=sim_re,
    )


def _build_gyroid(p: DesignParams):
    from parapygui.gyroid import GyroidMesh
    il, iw, ih = _interior(p)
    ctrl = [(il/2, iw/2, ih/2)]
    k = [p.initial_wavenumber]
    return GyroidMesh(
        length=il, width=iw, height=ih,
        ctrl_locations=ctrl,
        kx=k, ky=k, kz=k,
        iso_level=p.iso_level,
        resolution=p.resolution,
    )


def _build_mfg(gyroid, p: DesignParams):
    from parapygui.manufacturability import ManufacturabilityAnalysis
    from math import pi
    uc = 2 * pi / p.initial_wavenumber
    return ManufacturabilityAnalysis(
        face_normals=gyroid.face_normals,
        face_areas=gyroid.face_areas,
        solidity=gyroid.solidity,
        unit_cell_size=uc,
        max_overhang_angle=p.max_overhang_angle,
        min_feature_size=p.min_feature_size,
    )


# ── routes ───────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the single-page frontend."""
    html = _STATIC / "index.html"
    if html.exists():
        return HTMLResponse(html.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Frontend not found — place index.html in parapygui/static/</h1>")


@app.post("/api/compute")
async def compute(p: DesignParams) -> JSONResponse:
    """Compute all design metrics for the given parameters.

    Fast path: does NOT run full marching cubes.  Returns sizing, flow,
    and a quick solidity estimate from the gyroid field (no mesh).
    """
    try:
        from math import pi
        import numpy as np

        fluid = _build_fluid()
        dh = _hydraulic_diam(p)
        re = p.inflow_velocity * dh / fluid.kinematic_viscosity
        sizing = _build_sizing(p, fluid, dh, re)

        # Quick solidity — evaluate field on a coarse grid (no marching cubes)
        il, iw, ih = _interior(p)
        n = 30
        xs = np.linspace(0, il, n); ys = np.linspace(0, iw, n); zs = np.linspace(0, ih, n)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing='ij')
        k = p.initial_wavenumber
        F = (np.sin(k*X)*np.cos(k*Y) +
             np.sin(k*Y)*np.cos(k*Z) +
             np.sin(k*Z)*np.cos(k*X))
        solidity = float((np.abs(F) < p.iso_level).mean())
        solid_vol = solidity * il * iw * ih
        mass_g = solid_vol * 4430 * 1e3   # Ti-6Al-4V, grams

        # Manufacturability (simplified — from solidity + wavenumber only)
        uc = 2 * pi / k
        est_wall_mm = solidity * uc / pi * 1e3

        return JSONResponse({
            "ok": True,
            "flow": {
                "reynolds": round(re, 1),
                "prandtl":  round(fluid.prandtl_number, 3),
            },
            "sizing": sizing.summary,
            "lattice": {
                "solidity":       round(solidity, 4),
                "mass_g":         round(mass_g, 1),
                "unit_cell_mm":   round(uc * 1e3, 2),
                "est_wall_mm":    round(est_wall_mm, 3),
            },
            "manufacturability": {
                "est_wall_mm":          round(est_wall_mm, 3),
                "min_feature_mm":       round(p.min_feature_size * 1e3, 3),
                "wall_ok":              est_wall_mm >= p.min_feature_size * 1e3,
            },
        })
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.post("/api/stl")
async def generate_stl(p: DesignParams) -> StreamingResponse:
    """Generate the gyroid mesh and stream it as a binary STL.

    This is the slow endpoint (~1–3 s depending on resolution).
    The frontend calls this after the user finishes adjusting sliders.
    """
    try:
        gyroid = _build_gyroid(p)
        verts, faces, _ = gyroid.mesh

        # Build binary STL in memory
        import numpy as np
        tris = verts[faces]
        n = np.cross(tris[:,1]-tris[:,0], tris[:,2]-tris[:,0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        n = np.divide(n, ln, out=np.zeros_like(n), where=ln>0)

        buf = io.BytesIO()
        buf.write(b"\0" * 80)
        buf.write(struct.pack("<I", len(faces)))
        for i in range(len(faces)):
            buf.write(struct.pack("<3f", *n[i]))
            for v in tris[i]:
                buf.write(struct.pack("<3f", *v))
            buf.write(struct.pack("<H", 0))
        buf.seek(0)

        # Also return metrics as a header
        metrics = {
            "solidity":    round(gyroid.solidity, 4),
            "mass_g":      round(gyroid.mass * 1e3, 1),
            "surface_cm2": round(gyroid.surface_area * 1e4, 1),
            "n_triangles": gyroid.n_triangles,
        }

        return StreamingResponse(
            buf,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=gyroid.stl",
                "X-Metrics": json.dumps(metrics),
                "Access-Control-Expose-Headers": "X-Metrics",
            },
        )
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.post("/api/simulate/start")
async def sim_start(p: SimStartParams) -> JSONResponse:
    """Push the design config, then start (baseline or optimisation)."""
    try:
        from parapygui.simulation import SimulationConnector
        # 1. push the user's design to the server
        _push_design_config(p.design)
        # 2. start the run
        sim = SimulationConnector(host=p.design.grpc_host,
                                  port=p.design.grpc_port)
        extra = ["--optimise"] if p.optimise else None
        msg = sim.start(extra_args=extra)
        return JSONResponse({"ok": True, "message": msg, "pushed_config": True})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.post("/api/simulate/stop")
async def sim_stop(p: SimStartParams) -> JSONResponse:
    try:
        from parapygui.simulation import SimulationConnector
        msg = SimulationConnector(host=p.design.grpc_host,
                                  port=p.design.grpc_port).stop()
        return JSONResponse({"ok": True, "message": msg})
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.get("/api/simulate/status")
async def sim_status(host: str = "localhost", port: int = 50051) -> JSONResponse:
    try:
        from parapygui.simulation import SimulationConnector
        status = SimulationConnector(host=host, port=port).server_status
        return JSONResponse({"ok": True, "status": status})
    except Exception as exc:
        return JSONResponse({"ok": False, "status": "unreachable", "error": str(exc)})


@app.get("/api/simulate/history")
async def sim_history(host: str = "localhost", port: int = 50051) -> JSONResponse:
    try:
        from parapygui.simulation import SimulationConnector
        from parapygui.optimization_history import OptimizationHistory
        raw = SimulationConnector(host=host, port=port).optimisation_history
        h = OptimizationHistory(raw_history=raw)
        return JSONResponse({
            "ok": True,
            "n_iterations": h.n_iterations,
            "converged": h.has_converged,
            "outlet_temperature": h.outlet_temperature,
            "mechanical_dissipation": h.mechanical_dissipation,
            "objective": h.objective,
            "iterations": h.iterations,
            "latest": h.latest,
        })
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.post("/api/report")
async def generate_report(p: DesignParams) -> FileResponse:
    """Generate the PDF design report and serve it for download."""
    try:
        from math import pi
        fluid = _build_fluid()
        dh = _hydraulic_diam(p)
        re = p.inflow_velocity * dh / fluid.kinematic_viscosity
        sizing = _build_sizing(p, fluid, dh, re)
        il, iw, ih = _interior(p)

        summary = {
            "encapsulation": {
                "length_mm": round(p.enc_length*1e3,2),
                "width_mm":  round(p.enc_width*1e3,2),
                "height_mm": round(p.enc_height*1e3,2),
                "wall_mm":   round(p.enc_wall_thickness*1e3,2),
                "Dh_mm":     round(dh*1e3,3),
            },
            "flow": {"Re": round(re,1), "Pr": round(fluid.prandtl_number,3),
                     "T_in_K": p.inflow_temperature},
            "lattice": {"tpms": "gyroid",
                        "k_rad_m": p.initial_wavenumber,
                        "unit_cell_mm": round(2*pi/p.initial_wavenumber*1e3,2)},
            "sizing": sizing.summary,
        }

        from parapygui.reporting import ReportGenerator
        rg = ReportGenerator(output_dir="outputs", design_summary=summary)
        path = rg.generate()
        return FileResponse(path, media_type="application/pdf",
                            filename="design_report.pdf")
    except Exception as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=500)


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "heat-exchanger-kbe"})
