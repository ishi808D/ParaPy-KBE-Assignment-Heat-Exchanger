# -*- coding: utf-8 -*-
"""
workflow.py — Logic layer for the workflow wizard.

Maps ParaPy Inputs ↔ gyroid_case_config.yaml keys via gRPC.
Config keys verified against actual server output.
"""

import json
import math
import threading
import time

import wx

from .GUIwxformbuilder import WorkflowWizardFrame

# gRPC imports (live at repo root)
import sys, os
_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

import grpc
import gyroid_service_pb2 as pb2
import gyroid_service_pb2_grpc as pb2_grpc

# ---------------------------------------------------------------------------
# Plotly HTML helpers
# ---------------------------------------------------------------------------

_PLOTLY_CDN = "https://cdn.plot.ly/plotly-2.35.0.min.js"

def _plotly_html(traces, layout):
    return (f'<!DOCTYPE html><html><head><script src="{_PLOTLY_CDN}"></script>'
            f'<style>html,body{{margin:0;padding:0;width:100%;height:100%}}</style>'
            f'</head><body><div id="p" style="width:100%;height:100%"></div><script>'
            f'Plotly.newPlot("p",{json.dumps(traces)},{json.dumps(layout)},'
            f'{{responsive:true}})</script></body></html>')

def _convergence_html(iters, objs, cstrs=None, title="Convergence"):
    traces = [{"x": iters, "y": objs, "mode": "lines+markers", "name": "Objective"}]
    if cstrs:
        traces.append({"x": iters, "y": cstrs, "mode": "lines",
                       "name": "Constraint", "line": {"dash": "dash"}})
    layout = {"title": title, "xaxis": {"title": "Iteration"},
              "yaxis": {"title": "Value"}, "margin": {"t": 40, "b": 40, "l": 55, "r": 20},
              "template": "plotly_white"}
    return _plotly_html(traces, layout)

def _empty_html(msg="Waiting for data…"):
    return (f'<html><body style="display:flex;align-items:center;justify-content:center;'
            f'height:100%;color:#999;font-family:sans-serif"><p>{msg}</p></body></html>')

# ---------------------------------------------------------------------------
# gRPC wrapper
# ---------------------------------------------------------------------------

class GrpcConnection:
    def __init__(self, host="localhost", port=50051):
        self.host, self.port = host, port
        self._channel = None; self._stub = None

    @property
    def stub(self):
        if self._stub is None:
            self._channel = grpc.insecure_channel(f"{self.host}:{self.port}")
            self._stub = pb2_grpc.GyroidOptimizerStub(self._channel)
        return self._stub

    def close(self):
        if self._channel: self._channel.close()
        self._channel = self._stub = None

    # thin wrappers matching the protobuf API
    def patch_config(self, d):   return self.stub.PatchConfig(pb2.PatchConfigRequest(json_patch=json.dumps(d)))
    def start_run(self, a=None): return self.stub.StartRun(pb2.StartRunRequest(extra_args=a or []))
    def stop_run(self):          return self.stub.StopRun(pb2.Empty())
    def get_status(self):        return self.stub.GetRunStatus(pb2.Empty())
    def stream_output(self):     return self.stub.StreamOutput(pb2.Empty())
    def get_latest(self):        return self.stub.GetLatestMetrics(pb2.Empty())
    def get_history(self):       return self.stub.GetHistory(pb2.Empty())
    def start_stl(self, a=None): return self.stub.StartStlExport(pb2.StlExportRequest(extra_args=a or []))
    def get_stl_status(self):    return self.stub.GetStlStatus(pb2.Empty())
    def download_stl(self, w):   return self.stub.DownloadStl(pb2.StlFileRequest(which=w))

# ---------------------------------------------------------------------------
# Wizard implementation
# ---------------------------------------------------------------------------

class WorkflowWizard(WorkflowWizardFrame):

    def __init__(self, parent, parapy_obj):
        super().__init__(parent, parapy_obj)
        self._page = 0
        self._opt_iters, self._opt_objs, self._opt_cstrs = [], [], []
        self._stop = threading.Event()
        self._last_obj_path = None
        self._last_stl_paths = []
        self._sim_running = False       # True while baseline or optimization is active
        self._completed = set()

        # Create default input/output folders
        from pathlib import Path
        Path("inputs").mkdir(exist_ok=True)
        Path("outputs").mkdir(exist_ok=True)          # tracks completed workflow steps: {"baseline", "optimize"}

        self._grpc = GrpcConnection(
            host=getattr(parapy_obj, "grpc_host", "localhost"),
            port=getattr(parapy_obj, "grpc_port", 50051))

        for wv in [self.m_webviewBaseline,
                    self.m_webviewConvergence, self.m_webviewResults]:
            wv.SetPage(_empty_html(), "")

        self._load_from_parapy()
        self._try_load_from_server()
        self._update_nav()
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _on_close(self, evt):
        self._stop.set(); self._grpc.close(); evt.Skip()

    # =================================================================
    # Load state from ParaPy / from server
    # =================================================================

    def _load_from_parapy(self):
        """Pull ParaPy @Input values into spinners.
        Note: ParaPy stores geometry in metres; GUI spinners show mm.
        """
        obj = self.parapy_obj
        if not obj: return

        # (spinner, parapy_attr, fallback, multiply_for_display)
        pairs = [
            # geometry: m → mm
            (self.m_spinSizeX,     "enc_length",          0.10,  1000),
            (self.m_spinSizeY,     "enc_width",           0.05,  1000),
            (self.m_spinSizeZ,     "enc_height",          0.05,  1000),
            (self.m_spinEncapWall, "enc_wall_thickness",  0.002, 1000),
            # port bore sizes: m → mm
            (self.m_spinInWinSX,   "inlet_bore_width",    0.010, 1000),
            (self.m_spinInWinSY,   "inlet_bore_height",   0.015, 1000),
            (self.m_spinOutWinSX,  "outlet_bore_width",   0.010, 1000),
            (self.m_spinOutWinSY,  "outlet_bore_height",  0.015, 1000),
            # inlet / outlet (no conversion)
            (self.m_spinInletVel,  "inflow_velocity",     2.0,  1),
            (self.m_spinInletTemp, "inflow_temperature",  380,  1),
            (self.m_spinOutletP,   "outlet_pressure",     0.0,  1),
            # material / thermal
            (self.m_spinTexterior, "exterior_temperature", 270, 1),
            (self.m_spinTinitial,  "exterior_temperature", 270, 1),
            # optimization params
            (self.m_spinMeanTMax,  "meantT_max",    340,     1),
            (self.m_spinDissPMax,  "dissPower_max", 2800000, 1),
            (self.m_spinWallCells, "opt_wall_cells", 6,      1),
            (self.m_spinUnitCells, "opt_unit_cells", 75,     1),
            (self.m_spinAmTheta,   "am_theta",       45,     1),
            (self.m_spinMaxIter,   "max_iterations", 100,    1),
            (self.m_spinKbound,    "kbound",         0.08,   1),
        ]
        for spinner, attr, fallback, scale in pairs:
            val = getattr(obj, attr, fallback)
            spinner.SetValue(float(val) * scale)

        # cores is a SpinCtrl (int), not SpinCtrlDouble
        self.m_spinCores.SetValue(8)

        # no_overhang and opt_mode
        try:
            self.m_chkNoOverhang.SetValue(bool(getattr(obj, "no_overhang", False)))
        except Exception:
            pass
        try:
            mode = getattr(obj, "opt_mode", "pressure")
            self.m_radioMode.SetSelection(0 if mode == "pressure" else 1)
        except Exception:
            pass

        # kinematic viscosity and density come from the fluid Part
        try:
            self.m_spinNu.SetValue(obj.fluid.kinematic_viscosity)
            self.m_spinRhoFluid.SetValue(obj.fluid.density)
        except Exception:
            self.m_spinNu.SetValue(1e-6)
            self.m_spinRhoFluid.SetValue(1000.0)

        # lattice preview parameters

    def _write_gui_to_parapy(self):
        """Push GUI spinner values back to ParaPy @Inputs.
        Geometry spinners are in mm; ParaPy stores metres.
        """
        obj = self.parapy_obj
        if not obj: return

        # (spinner, parapy_attr, divide_for_storage)
        pairs = [
            (self.m_spinSizeX,     "enc_length",         1000),
            (self.m_spinSizeY,     "enc_width",          1000),
            (self.m_spinSizeZ,     "enc_height",         1000),
            (self.m_spinEncapWall, "enc_wall_thickness", 1000),
            (self.m_spinInWinSX,   "inlet_bore_width",   1000),
            (self.m_spinInWinSY,   "inlet_bore_height",  1000),
            (self.m_spinOutWinSX,  "outlet_bore_width",  1000),
            (self.m_spinOutWinSY,  "outlet_bore_height", 1000),
            (self.m_spinInletVel,  "inflow_velocity",    1),
            (self.m_spinInletTemp, "inflow_temperature", 1),
            (self.m_spinOutletP,   "outlet_pressure",    1),
            (self.m_spinTexterior, "exterior_temperature", 1),
            (self.m_spinMeanTMax,  "meantT_max",    1),
            (self.m_spinDissPMax,  "dissPower_max", 1),
            (self.m_spinWallCells, "opt_wall_cells", 1),
            (self.m_spinUnitCells, "opt_unit_cells", 1),
            (self.m_spinAmTheta,   "am_theta",       1),
            (self.m_spinMaxIter,   "max_iterations", 1),
            (self.m_spinKbound,    "kbound",         1),
        ]
        for spinner, attr, scale in pairs:
            try:
                setattr(obj, attr, spinner.GetValue() / scale)
            except Exception as e:
                print(f"[workflow] _write_gui_to_parapy: {attr} — {e}")
        try:
            obj.no_overhang = bool(self.m_chkNoOverhang.GetValue())
        except Exception as e:
            print(f"[workflow] _write_gui_to_parapy: no_overhang — {e}")
        try:
            obj.opt_mode = "pressure" if self.m_radioMode.GetSelection() == 0 else "heat"
        except Exception as e:
            print(f"[workflow] _write_gui_to_parapy: opt_mode — {e}")
        # lattice preview

    def _update_parapy_geometry(self):
        """Force ParaPy to recompute geometry after wizard values change.
        Writing to @Input attributes triggers ParaPy's dependency tracking,
        which automatically invalidates and recomputes dependent @Attributes
        and @Parts (including the encapsulation geometry in the 3D viewport).
        """
        obj = self.parapy_obj
        if not obj:
            return

        geo_writes = [
            ("enc_length",         self.m_spinSizeX.GetValue()     / 1000),
            ("enc_width",          self.m_spinSizeY.GetValue()     / 1000),
            ("enc_height",         self.m_spinSizeZ.GetValue()     / 1000),
            ("enc_wall_thickness", self.m_spinEncapWall.GetValue() / 1000),
            ("inlet_bore_width",   self.m_spinInWinSX.GetValue()   / 1000),
            ("inlet_bore_height",  self.m_spinInWinSY.GetValue()   / 1000),
            ("outlet_bore_width",  self.m_spinOutWinSX.GetValue()  / 1000),
            ("outlet_bore_height", self.m_spinOutWinSY.GetValue()  / 1000),
            ("baseline_dissipation", getattr(self, "_final_dissip", 0)),
            ("baseline_mean_temp",   getattr(self, "_final_meanT",  0)),
        ]
        errors = []
        for attr, val in geo_writes:
            try:
                setattr(obj, attr, val)
            except Exception as e:
                errors.append(f"{attr}: {e}")
                print(f"[workflow] _update_parapy_geometry: {attr} — {e}")

        if errors:
            self.m_statusLabel.SetLabel(f"Partial update — {errors[0]}")
        else:
            self.m_statusLabel.SetLabel("ParaPy model updated — check 3D viewport.")

    def onCellsChanged(self, event):
        """Update the total cell count label when any cell spinner changes."""
        cx = self.m_spinCellsX.GetValue()
        cy = self.m_spinCellsY.GetValue()
        cz = self.m_spinCellsZ.GetValue()
        total = cx * cy * cz
        self.m_lblTotalCells.SetLabel(f"  = {total:,} cells")

    def _try_load_from_server(self):
        """Try to pull the current config from the running container
        and populate spinners (useful if container already has a config)."""
        try:
            resp = self._grpc.stub.GetConfig(pb2.Empty())
            if resp.success:
                import yaml
                cfg = yaml.safe_load(resp.yaml_content)
                sz = cfg.get("geometry", {}).get("size_mm", [250, 250, 300])
                self.m_spinSizeX.SetValue(sz[0])
                self.m_spinSizeY.SetValue(sz[1])
                self.m_spinSizeZ.SetValue(sz[2])
                self.m_spinInletVel.SetValue(cfg.get("inlet", {}).get("velocity_magnitude", 2.0))
                self.m_spinInletTemp.SetValue(cfg.get("inlet", {}).get("temperature", 380.0))
                self.m_spinOutletP.SetValue(cfg.get("outlet", {}).get("pressure", 0.0))
                self.m_spinTexterior.SetValue(cfg.get("material", {}).get("Texterior", 270.0))
                self.m_spinTinitial.SetValue(cfg.get("thermal", {}).get("initial_temperature", 270.0))
                self.m_spinNu.SetValue(cfg.get("material", {}).get("nu", 1e-6))
                self.m_spinRhoFluid.SetValue(cfg.get("material", {}).get("rho_fluid", 1000.0))
                self.m_spinEncapWall.SetValue(cfg.get("geometry", {}).get("encap_wall_mm", 3.0))
                opt = cfg.get("optimization", {})
                self.m_spinMeanTMax.SetValue(opt.get("meantT_max", 340))
                self.m_spinDissPMax.SetValue(opt.get("dissPower_max", 2800000))
                self.m_spinWallCells.SetValue(opt.get("wall", 6))
                self.m_spinUnitCells.SetValue(opt.get("unit", 75))
                self.m_spinAmTheta.SetValue(opt.get("am_theta", 45))
                self.m_spinKbound.SetValue(opt.get("kbound", 0.08))
                self.m_spinMaxIter.SetValue(cfg.get("run", {}).get("iters", 100))
                mode = opt.get("mode", "pressure")
                self.m_radioMode.SetSelection(0 if mode == "pressure" else 1)
                self.m_chkNoOverhang.SetValue(opt.get("no_overhang", False))
                # inlet/outlet windows
                iwo = cfg.get("inlet", {}).get("window_origin_mm", [10, 10])
                iws = cfg.get("inlet", {}).get("window_size_mm", [10, 15])
                self.m_spinInWinOX.SetValue(iwo[0]); self.m_spinInWinOY.SetValue(iwo[1])
                self.m_spinInWinSX.SetValue(iws[0]); self.m_spinInWinSY.SetValue(iws[1])
                owo = cfg.get("outlet", {}).get("window_origin_mm", [220, 220])
                ows = cfg.get("outlet", {}).get("window_size_mm", [10, 15])
                self.m_spinOutWinOX.SetValue(owo[0]); self.m_spinOutWinOY.SetValue(owo[1])
                self.m_spinOutWinSX.SetValue(ows[0]); self.m_spinOutWinSY.SetValue(ows[1])
                self.m_statusLabel.SetLabel("Loaded config from server.")
        except Exception as e:
            self.m_statusLabel.SetLabel(f"Server not reachable: {e}")

    # =================================================================
    # Build the REAL config patch dict
    # Keys verified against actual gyroid_case_config.yaml
    # =================================================================

    def _build_config_patch(self):
        """Map GUI spinners → server config dot-notation keys.

        geometry.size_mm regenerates the blockMeshDict — inlet/outlet
        window coordinates MUST be within the domain bounds.
        Validation is performed before building the patch.
        """
        # ── Validate window coordinates fit inside domain ──
        size_x = self.m_spinSizeX.GetValue()
        size_y = self.m_spinSizeY.GetValue()
        size_z = self.m_spinSizeZ.GetValue()
        # Flow axis is z by default; transverse axes are x and y
        # Window coords are 2D on the transverse plane
        transverse = [size_x, size_y]  # for flow_axis=z

        for label, ox, oy, sx, sy in [
            ("Inlet",
             self.m_spinInWinOX.GetValue(), self.m_spinInWinOY.GetValue(),
             self.m_spinInWinSX.GetValue(), self.m_spinInWinSY.GetValue()),
            ("Outlet",
             self.m_spinOutWinOX.GetValue(), self.m_spinOutWinOY.GetValue(),
             self.m_spinOutWinSX.GetValue(), self.m_spinOutWinSY.GetValue()),
        ]:
            if ox + sx > transverse[0] + 0.01:
                raise ValueError(
                    f"{label} window X: origin({ox}) + size({sx}) = {ox+sx} "
                    f"exceeds domain width {transverse[0]}mm")
            if oy + sy > transverse[1] + 0.01:
                raise ValueError(
                    f"{label} window Y: origin({oy}) + size({sy}) = {oy+sy} "
                    f"exceeds domain height {transverse[1]}mm")

        p = {}

        # ── Geometry (regenerates blockMeshDict) ──
        p["geometry.size_mm"] = [size_x, size_y, size_z]
        p["geometry.cells"] = [
            self.m_spinCellsX.GetValue(),
            self.m_spinCellsY.GetValue(),
            self.m_spinCellsZ.GetValue(),
        ]
        p["geometry.encap_wall_mm"] = self.m_spinEncapWall.GetValue()

        # ── Inlet (windows must fit inside geometry.size_mm) ──
        p["inlet.velocity_magnitude"] = self.m_spinInletVel.GetValue()
        p["inlet.temperature"] = self.m_spinInletTemp.GetValue()
        p["inlet.window_origin_mm"] = [
            self.m_spinInWinOX.GetValue(),
            self.m_spinInWinOY.GetValue(),
        ]
        p["inlet.window_size_mm"] = [
            self.m_spinInWinSX.GetValue(),
            self.m_spinInWinSY.GetValue(),
        ]

        # ── Outlet (windows must fit inside geometry.size_mm) ──
        p["outlet.pressure"] = self.m_spinOutletP.GetValue()
        p["outlet.window_origin_mm"] = [
            self.m_spinOutWinOX.GetValue(),
            self.m_spinOutWinOY.GetValue(),
        ]
        p["outlet.window_size_mm"] = [
            self.m_spinOutWinSX.GetValue(),
            self.m_spinOutWinSY.GetValue(),
        ]

        # ── Material / thermal ──
        p["material.Texterior"] = self.m_spinTexterior.GetValue()
        p["material.nu"] = self.m_spinNu.GetValue()
        p["material.rho_fluid"] = self.m_spinRhoFluid.GetValue()
        p["thermal.initial_temperature"] = self.m_spinTinitial.GetValue()

        # ── Optimization ──
        mode = "pressure" if self.m_radioMode.GetSelection() == 0 else "heat"
        p["optimization.mode"] = mode
        p["optimization.meantT_max"] = self.m_spinMeanTMax.GetValue()
        p["optimization.dissPower_max"] = self.m_spinDissPMax.GetValue()
        p["optimization.wall"] = int(self.m_spinWallCells.GetValue())
        p["optimization.unit"] = int(self.m_spinUnitCells.GetValue())
        p["optimization.am_theta"] = self.m_spinAmTheta.GetValue()
        p["optimization.no_overhang"] = self.m_chkNoOverhang.GetValue()
        p["optimization.kbound"] = self.m_spinKbound.GetValue()

        # ── Run control ──
        p["run.iters"] = int(self.m_spinMaxIter.GetValue())
        p["run.parallel"] = self.m_spinCores.GetValue()

        return p

    # =================================================================
    # Navigation (dependency-aware)
    # =================================================================

    def _go_to(self, idx):
        idx = max(0, min(idx, self.NUM_PAGES - 1))
        self._page = idx
        self.m_simplebook.ChangeSelection(idx)
        self.m_headerLabel.SetLabel(self.PAGE_TITLES[idx])
        self._update_nav()

    def _update_nav(self):
        # Back: disabled on page 0 or while a simulation is running
        self.m_btnBack.Enable(self._page > 0 and not self._sim_running)

        # Next: disabled while sim running; on certain pages, require completion
        can_next = not self._sim_running
        if self._page == 2 and "baseline" not in self._completed:
            can_next = False  # must run baseline before advancing
        if self._page == 4 and "optimize" not in self._completed:
            can_next = False  # must run optimization before advancing

        self.m_btnNext.Enable(can_next)
        self.m_btnNext.SetLabel("Finish" if self._page == self.NUM_PAGES - 1 else "Next ▶")

        # Export buttons on page 5: only enabled after optimization
        if hasattr(self, "m_btnExportSTL"):
            exports_ok = "optimize" in self._completed
            self.m_btnExportSTL.Enable(exports_ok)
            self.m_btnQuadMesh.Enable(exports_ok)

    def onBack(self, event):
        if self._sim_running:
            return  # safety: can't go back during sim
        self._go_to(self._page - 1)

    def onNext(self, event):
        if self._sim_running:
            return
        if self._page == self.NUM_PAGES - 1:
            # Finish — write everything back to ParaPy to update geometry
            self._write_gui_to_parapy()
            self._update_parapy_geometry()
            self.Close()
            return
        if self._page == 0:
            self._write_gui_to_parapy()
            self._compute_sizing()
        elif self._page == 3:
            self._write_gui_to_parapy()
        self._go_to(self._page + 1)

    def _set_sim_running(self, running):
        """Update simulation state and refresh navigation."""
        self._sim_running = running
        self._update_nav()

    # =================================================================
    # Page 0: Apply geometry
    # =================================================================

    def onApplyGeom(self, event):
        self._write_gui_to_parapy()
        self._update_parapy_geometry()

    def onLoadJSON(self, event):
        """Load configuration from a JSON file (server YAML structure)."""
        import json
        from pathlib import Path
        inputs_dir = Path("inputs")
        inputs_dir.mkdir(exist_ok=True)
        dlg = wx.FileDialog(self, "Load Configuration", str(inputs_dir),
                            wildcard="JSON files (*.json)|*.json",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                with open(dlg.GetPath()) as f:
                    cfg = json.load(f)
                geo  = cfg.get("geometry", {})
                inl  = cfg.get("inlet", {})
                out  = cfg.get("outlet", {})
                mat  = cfg.get("material", {})
                thm  = cfg.get("thermal", {})
                opt  = cfg.get("optimization", {})
                run  = cfg.get("run", {})

                sz = geo.get("size_mm")
                if sz and len(sz) == 3:
                    self.m_spinSizeX.SetValue(sz[0])
                    self.m_spinSizeY.SetValue(sz[1])
                    self.m_spinSizeZ.SetValue(sz[2])
                cells = geo.get("cells")
                if cells and len(cells) == 3:
                    self.m_spinCellsX.SetValue(int(cells[0]))
                    self.m_spinCellsY.SetValue(int(cells[1]))
                    self.m_spinCellsZ.SetValue(int(cells[2]))
                if "encap_wall_mm" in geo:
                    self.m_spinEncapWall.SetValue(geo["encap_wall_mm"])

                if "velocity_magnitude" in inl:
                    self.m_spinInletVel.SetValue(inl["velocity_magnitude"])
                if "temperature" in inl:
                    self.m_spinInletTemp.SetValue(inl["temperature"])
                iwo = inl.get("window_origin_mm")
                if iwo and len(iwo) == 2:
                    self.m_spinInWinOX.SetValue(iwo[0])
                    self.m_spinInWinOY.SetValue(iwo[1])
                iws = inl.get("window_size_mm")
                if iws and len(iws) == 2:
                    self.m_spinInWinSX.SetValue(iws[0])
                    self.m_spinInWinSY.SetValue(iws[1])

                if "pressure" in out:
                    self.m_spinOutletP.SetValue(out["pressure"])
                owo = out.get("window_origin_mm")
                if owo and len(owo) == 2:
                    self.m_spinOutWinOX.SetValue(owo[0])
                    self.m_spinOutWinOY.SetValue(owo[1])
                ows = out.get("window_size_mm")
                if ows and len(ows) == 2:
                    self.m_spinOutWinSX.SetValue(ows[0])
                    self.m_spinOutWinSY.SetValue(ows[1])

                if "Texterior" in mat:
                    self.m_spinTexterior.SetValue(mat["Texterior"])
                if "nu" in mat:
                    self.m_spinNu.SetValue(mat["nu"])
                if "rho_fluid" in mat:
                    self.m_spinRhoFluid.SetValue(mat["rho_fluid"])

                if "initial_temperature" in thm:
                    self.m_spinTinitial.SetValue(thm["initial_temperature"])

                if "mode" in opt:
                    self.m_radioMode.SetSelection(0 if opt["mode"] == "pressure" else 1)
                if "meantT_max" in opt:
                    self.m_spinMeanTMax.SetValue(opt["meantT_max"])
                if "dissPower_max" in opt:
                    self.m_spinDissPMax.SetValue(opt["dissPower_max"])
                if "wall" in opt:
                    self.m_spinWallCells.SetValue(opt["wall"])
                if "unit" in opt:
                    self.m_spinUnitCells.SetValue(opt["unit"])
                if "am_theta" in opt:
                    self.m_spinAmTheta.SetValue(opt["am_theta"])
                if "no_overhang" in opt:
                    self.m_chkNoOverhang.SetValue(bool(opt["no_overhang"]))
                if "kbound" in opt:
                    self.m_spinKbound.SetValue(opt["kbound"])

                if "iters" in run:
                    self.m_spinMaxIter.SetValue(run["iters"])
                if "parallel" in run:
                    self.m_spinCores.SetValue(int(run["parallel"]))

                self.m_statusLabel.SetLabel(f"Loaded: {dlg.GetPath()}")
            except Exception as e:
                wx.MessageBox(f"Failed to load:\n{e}", "Error", wx.OK|wx.ICON_ERROR)
        dlg.Destroy()

    def onSaveJSON(self, event):
        """Save current configuration to inputs/config.json."""
        import json
        from pathlib import Path
        inputs_dir = Path("inputs")
        inputs_dir.mkdir(exist_ok=True)
        path = inputs_dir / "config.json"
        if True:
            cfg = {
                "geometry": {
                    "size_mm": [
                        self.m_spinSizeX.GetValue(),
                        self.m_spinSizeY.GetValue(),
                        self.m_spinSizeZ.GetValue(),
                    ],
                    "cells": [
                        int(self.m_spinCellsX.GetValue()),
                        int(self.m_spinCellsY.GetValue()),
                        int(self.m_spinCellsZ.GetValue()),
                    ],
                    "encap_wall_mm": self.m_spinEncapWall.GetValue(),
                },
                "inlet": {
                    "velocity_magnitude": self.m_spinInletVel.GetValue(),
                    "temperature":        self.m_spinInletTemp.GetValue(),
                    "window_origin_mm": [
                        self.m_spinInWinOX.GetValue(),
                        self.m_spinInWinOY.GetValue(),
                    ],
                    "window_size_mm": [
                        self.m_spinInWinSX.GetValue(),
                        self.m_spinInWinSY.GetValue(),
                    ],
                },
                "outlet": {
                    "pressure": self.m_spinOutletP.GetValue(),
                    "window_origin_mm": [
                        self.m_spinOutWinOX.GetValue(),
                        self.m_spinOutWinOY.GetValue(),
                    ],
                    "window_size_mm": [
                        self.m_spinOutWinSX.GetValue(),
                        self.m_spinOutWinSY.GetValue(),
                    ],
                },
                "material": {
                    "Texterior": self.m_spinTexterior.GetValue(),
                    "nu":        self.m_spinNu.GetValue(),
                    "rho_fluid": self.m_spinRhoFluid.GetValue(),
                },
                "thermal": {
                    "initial_temperature": self.m_spinTinitial.GetValue(),
                },
                "optimization": {
                    "mode":          "pressure" if self.m_radioMode.GetSelection() == 0 else "heat",
                    "meantT_max":    self.m_spinMeanTMax.GetValue(),
                    "dissPower_max": self.m_spinDissPMax.GetValue(),
                    "wall":          int(self.m_spinWallCells.GetValue()),
                    "unit":          int(self.m_spinUnitCells.GetValue()),
                    "am_theta":      self.m_spinAmTheta.GetValue(),
                    "no_overhang":   self.m_chkNoOverhang.GetValue(),
                    "kbound":        self.m_spinKbound.GetValue(),
                },
                "run": {
                    "iters":    int(self.m_spinMaxIter.GetValue()),
                    "parallel": int(self.m_spinCores.GetValue()),
                },
            }
            try:
                with open(path, "w") as f:
                    json.dump(cfg, f, indent=2)
                self.m_statusLabel.SetLabel(f"Config saved: {path}")
            except Exception as e:
                wx.MessageBox(f"Failed to save:\n{e}", "Error", wx.OK|wx.ICON_ERROR)

    # =================================================================
    # Page 1: Semi-empirical sizing (reads ParaPy @Attributes)
    # =================================================================

    def _compute_sizing(self):
        obj = self.parapy_obj
        if not obj:
            self.m_statusLabel.SetLabel("No ParaPy object."); return
        try:
            self.m_txtReynolds.SetValue(f"{obj.reynolds_number:.1f}")
            self.m_txtSolidity.SetValue(f"{obj.solidity:.4f}")
            self.m_txtNusselt.SetValue(f"{obj.nusselt_number:.2f}")
            self.m_txtFriction.SetValue(f"{obj.friction_factor:.5f}")
            self.m_txtPressureDrop.SetValue(f"{obj.pressure_drop:.2f}")
            self.m_txtDh.SetValue(f"{obj.hydraulic_diameter:.4f}")
        except AttributeError as e:
            self.m_statusLabel.SetLabel(f"Missing attribute: {e}"); return
        self.m_statusLabel.SetLabel("Sizing computed.")

    # =================================================================
    # Page 2: Baseline simulation (real gRPC)
    # =================================================================

    def onRunBaseline(self, event):
        self.m_btnRunBaseline.Enable(False)
        self.m_statusLabel.SetLabel("Starting baseline simulation…")
        self.m_gaugeBaseline.SetValue(0)
        self._stop.clear()
        self._set_sim_running(True)
        threading.Thread(target=self._run_worker, args=("baseline",), daemon=True).start()

    # =================================================================
    # Page 4: Optimization (real gRPC)
    # =================================================================

    def onStartOpt(self, event):
        self.m_btnStartOpt.Enable(False)
        self.m_statusLabel.SetLabel("Starting optimisation…")
        self._opt_iters.clear(); self._opt_objs.clear(); self._opt_cstrs.clear()
        self._stop.clear()
        self._set_sim_running(True)
        threading.Thread(target=self._run_worker, args=("optimize",), daemon=True).start()

    # =================================================================
    # Shared gRPC worker (used for both baseline and optimization)
    # =================================================================

    def _run_worker(self, mode):
        """mode = 'baseline' or 'optimize'. Both do PatchConfig → StartRun → StreamOutput."""
        log_ctrl = self.m_txtBaselineLog if mode == "baseline" else self.m_txtSolverLog
        webview = self.m_webviewBaseline if mode == "baseline" else self.m_webviewConvergence

        # Data parsed directly from OpenFOAM output lines
        residual_history = []    # list of (time_step, {field: residual})
        outer_iterations = []    # list of {iter, gamma_mean, solid_frac, ...}
        current_time_step = None
        current_residuals = {}

        import re

        try:
            # 1) Push config (includes validation)
            try:
                patch = self._build_config_patch()
            except ValueError as ve:
                wx.CallAfter(self._worker_error, mode, str(ve))
                return
            if mode == "baseline":
                patch["run.iters"] = 1  # single optimizer iteration for baseline
            resp = self._grpc.patch_config(patch)
            wx.CallAfter(log_ctrl.AppendText, f"Config: {resp.message}\n")

            # 2) Stop any existing run, then start fresh
            try:
                self._grpc.stop_run()
                time.sleep(1)
            except grpc.RpcError:
                pass
            resp = self._grpc.start_run()
            wx.CallAfter(log_ctrl.AppendText, f"Run: {resp.message}\n")
            if not resp.success:
                wx.CallAfter(self._worker_error, mode, resp.message); return

            # 3) Stream output — parse residuals and optimizer info in real time
            line_count = 0
            try:
                for line in self._grpc.stream_output():
                    if self._stop.is_set():
                        self._grpc.stop_run(); break

                    text = line.line
                    ts = time.strftime("%H:%M:%S", time.localtime(line.timestamp_ms / 1000))
                    pfx = "ERR" if line.is_stderr else "OUT"
                    wx.CallAfter(log_ctrl.AppendText, f"[{ts}][{pfx}] {text}\n")

                    # --- Parse OpenFOAM residual lines ---
                    # e.g. "smoothSolver:  Solving for Ux, Initial residual = 1, Final residual = 7.31e-08, No Iterations 2"
                    # e.g. "GAMG:  Solving for p, Initial residual = 1, Final residual = 0.001, No Iterations 50"
                    m_resid = re.search(
                        r'Solving for (\w+),.*Initial residual = ([\d.eE+-]+),.*Final residual = ([\d.eE+-]+)',
                        text)
                    if m_resid:
                        field = m_resid.group(1)
                        init_r = float(m_resid.group(2))
                        final_r = float(m_resid.group(3))
                        current_residuals[field] = final_r

                    # --- Parse "Time = N" lines (marks end of a time step) ---
                    m_time = re.match(r'^Time = (\d+)', text.strip())
                    if m_time:
                        t_step = int(m_time.group(1))
                        if current_residuals and t_step > 0:
                            residual_history.append((t_step, dict(current_residuals)))
                            current_residuals = {}
                            # Update convergence plot with residual data
                            wx.CallAfter(self._update_residual_plot,
                                         residual_history, webview)
                        current_time_step = t_step

                    # --- Parse outer iteration lines ---
                    # "Outer iteration 1  [mode: pressure]"
                    m_outer = re.search(r'Outer iteration (\d+)', text)
                    if m_outer:
                        outer_iter = int(m_outer.group(1))
                        outer_iterations.append({"iter": outer_iter})

                    # "gamma:  min=0.446  max=0.630  mean=0.539  solid_frac=0.461"
                    m_gamma = re.search(
                        r'gamma:\s+min=([\d.]+)\s+max=([\d.]+)\s+mean=([\d.]+)\s+solid_frac=([\d.]+)',
                        text)
                    if m_gamma and outer_iterations:
                        outer_iterations[-1].update({
                            "gamma_min": float(m_gamma.group(1)),
                            "gamma_max": float(m_gamma.group(2)),
                            "gamma_mean": float(m_gamma.group(3)),
                            "solid_frac": float(m_gamma.group(4)),
                        })

                    # Parse optimizer metrics from summary lines:
                    # "  DissPower = 1234.5"  or  "  meanT = 305.2"
                    # "  gradNorm = 0.0023"  or  "  G_oh = 1.5e-03"
                    for metric_name in ["DissPower", "Disspower", "dissPower",
                                        "meanT", "meantT", "MeanT",
                                        "gradNorm", "GradNorm",
                                        "G_oh", "volUse", "Voluse"]:
                        m_metric = re.search(
                            rf'{metric_name}\s*[=:]\s*([-+]?[\d.eE+-]+)', text)
                        if m_metric and outer_iterations:
                            outer_iterations[-1][metric_name] = float(m_metric.group(1))

                    # Also try tab/space separated optimizer history lines
                    # e.g. "  iter  dissPower  meanT  gradNorm  G_oh"
                    # followed by "  1    1234.5   305.2  0.0023   1.5e-3"

                    # Update multi-metric convergence plot when we have outer iteration data
                    if outer_iterations and len(outer_iterations) > len(self._opt_iters):
                        wx.CallAfter(self._update_optimizer_plot,
                                     outer_iterations, webview)

                    # --- Also poll gRPC metrics periodically ---
                    line_count += 1
                    if line_count % 50 == 0:
                        self._poll_grpc_metrics(mode, webview)

                    # Pulse gauge during baseline
                    if mode == "baseline":
                        wx.CallAfter(self.m_gaugeBaseline.Pulse)

            except grpc.RpcError as e:
                wx.CallAfter(log_ctrl.AppendText,
                             f"Stream ended: {e.details() if hasattr(e, 'details') else str(e)}\n")

            # 4) Final: try gRPC metrics, fall back to parsed data
            self._fetch_final_results(mode, residual_history, outer_iterations, webview)

        except grpc.RpcError as e:
            wx.CallAfter(self._worker_error, mode,
                         f"gRPC: {e.details() if hasattr(e, 'details') else str(e)}")
        except Exception as e:
            import traceback
            wx.CallAfter(self._worker_error, mode, f"{e}\n{traceback.format_exc()}")

    def _update_residual_plot(self, residual_history, webview):
        """Build a Plotly chart from parsed OpenFOAM residuals."""
        if not residual_history:
            return

        # Collect all field names
        all_fields = set()
        for _, resids in residual_history:
            all_fields.update(resids.keys())

        time_steps = [t for t, _ in residual_history]
        traces = []
        for field in sorted(all_fields):
            values = [resids.get(field, None) for _, resids in residual_history]
            traces.append({
                "x": time_steps,
                "y": values,
                "mode": "lines",
                "name": field,
            })

        layout = {
            "title": "Solver Residuals",
            "xaxis": {"title": "Time Step"},
            "yaxis": {"title": "Final Residual", "type": "log"},
            "margin": {"t": 40, "b": 40, "l": 55, "r": 20},
            "template": "plotly_white",
            "legend": {"x": 0.01, "y": 0.99},
        }
        webview.SetPage(_plotly_html(traces, layout), "")

    def _poll_grpc_metrics(self, mode, webview):
        """Try polling gRPC GetLatestMetrics — updates convergence if available."""
        try:
            m = self._grpc.get_latest()
            if m.available:
                row = m.latest
                # Log available keys for debugging
                keys = list(row.values.keys())
                if keys:
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"Metrics keys: {', '.join(keys)}")

                # Try to extract values with multiple possible key names
                for key_attempts, target_list in [
                    (["dissPower", "Disspower", "dissipation", "objective"], self._opt_objs),
                    (["meantT", "meanT", "MeanT", "temperature"], self._opt_cstrs),
                ]:
                    for k in key_attempts:
                        if k in row.values:
                            target_list.append(row.values[k])
                            break

                if self._opt_objs:
                    self._opt_iters = list(range(len(self._opt_objs)))
                    wx.CallAfter(webview.SetPage,
                                 _convergence_html(self._opt_iters, self._opt_objs,
                                                   self._opt_cstrs if self._opt_cstrs else None,
                                                   "Optimization Metrics"), "")
        except Exception:
            pass

    def _fetch_final_results(self, mode, residual_history, outer_iterations, webview):
        """Pull final results — try gRPC first, fall back to parsed data."""
        dissip = 0.0
        meanT = 0.0
        got_grpc = False

        # Try gRPC metrics
        try:
            m = self._grpc.get_latest()
            if m.available:
                row = m.latest
                keys = list(row.values.keys())
                wx.CallAfter(self.m_statusLabel.SetLabel,
                             f"Final metric keys: {keys}")

                for k in ["dissPower", "Disspower", "dissipation"]:
                    if k in row.values:
                        dissip = row.values[k]; break
                for k in ["meantT", "meanT", "MeanT"]:
                    if k in row.values:
                        meanT = row.values[k]; break
                got_grpc = True
        except Exception as e:
            wx.CallAfter(self.m_statusLabel.SetLabel, f"Metrics fetch: {e}")

        # Try gRPC history for full convergence
        try:
            hist = self._grpc.get_history()
            if hist.success and hist.rows:
                # Log the column names so we know what's available
                wx.CallAfter(self.m_statusLabel.SetLabel,
                             f"History columns: {hist.columns}")

                iters, objs, cstrs = [], [], []
                for i, row in enumerate(hist.rows):
                    iters.append(i)
                    val = 0.0
                    for k in ["dissPower", "Disspower", "dissipation", "objective"]:
                        if k in row.values:
                            val = row.values[k]; break
                    objs.append(val)
                    cval = 0.0
                    for k in ["meantT", "meanT", "MeanT", "constraint"]:
                        if k in row.values:
                            cval = row.values[k]; break
                    cstrs.append(cval)

                self._opt_iters, self._opt_objs, self._opt_cstrs = iters, objs, cstrs
                html = _convergence_html(iters, objs, cstrs, "Optimization History")
                target = self.m_webviewResults if mode == "optimize" else webview
                wx.CallAfter(target.SetPage, html, "")
        except Exception as e:
            wx.CallAfter(self.m_statusLabel.SetLabel, f"History fetch: {e}")

        # Fall back to parsed residual data for the convergence plot
        if residual_history and not got_grpc:
            wx.CallAfter(self._update_residual_plot, residual_history, webview)

        # Update result fields
        if mode == "baseline":
            wx.CallAfter(self._baseline_done, dissip, meanT)
        else:
            wx.CallAfter(self._opt_done, dissip, meanT)

    def _baseline_done(self, dissip, meanT):
        self.m_gaugeBaseline.SetValue(100)
        self.m_txtBaseDissip.SetLabel(f"{dissip:.2f}" if dissip else "—")
        self.m_txtBaseMeanT.SetLabel(f"{meanT:.2f}" if meanT else "—")
        self.m_btnRunBaseline.Enable(True)
        self.m_statusLabel.SetLabel("Baseline complete.")
        self._completed.add("baseline")
        self._set_sim_running(False)
        if self.parapy_obj:
            try:
                self.parapy_obj.baseline_dissipation = dissip
                self.parapy_obj.baseline_mean_temp = meanT
            except Exception: pass

    def _opt_done(self, dissip, meanT):
        self.m_txtOptDissip.SetValue(f"{dissip:.2f}")
        self.m_txtOptMeanT.SetValue(f"{meanT:.2f}")
        self.m_txtIterCount.SetValue(str(len(self._opt_iters)))
        self.m_txtConverged.SetValue("Yes" if self._opt_iters else "—")
        if self._opt_iters:
            self.m_webviewResults.SetPage(
                _convergence_html(self._opt_iters, self._opt_objs,
                                  self._opt_cstrs, "Final Convergence"), "")
        self.m_btnStartOpt.Enable(True)
        self.m_statusLabel.SetLabel("Optimisation complete.")
        self._completed.add("optimize")
        self._set_sim_running(False)
        if self.parapy_obj:
            try:
                self.parapy_obj.opt_dissipation = dissip
                self.parapy_obj.opt_mean_temp = meanT
            except Exception: pass

    def _worker_error(self, mode, msg):
        self.m_statusLabel.SetLabel(f"{mode} failed: {msg}")
        self._set_sim_running(False)
        if mode == "baseline":
            self.m_txtBaselineLog.AppendText(f"\n*** ERROR: {msg}\n")
            self.m_btnRunBaseline.Enable(True)
        else:
            self.m_txtSolverLog.AppendText(f"\n*** ERROR: {msg}\n")
            self.m_btnStartOpt.Enable(True)

    # =================================================================
    # Page 3: Apply optimizer settings
    # =================================================================

    def onApplyOpt(self, event):
        self._write_gui_to_parapy()
        self.m_statusLabel.SetLabel("Optimizer settings applied to model.")

    # =================================================================
    # Page 5: Export hooks
    # =================================================================

    def onExportSTL(self, event):
        """Download existing STL files from the container to outputs/."""
        from pathlib import Path
        out_dir = str(Path("outputs"))
        Path(out_dir).mkdir(exist_ok=True)
        self.m_btnExportSTL.Enable(False)
        self.m_statusLabel.SetLabel("Downloading STL…")
        threading.Thread(target=self._stl_download_worker,
                         args=(out_dir,), daemon=True).start()

    def _stl_download_worker(self, out_dir):
        from pathlib import Path
        saved = []

        # Try downloading existing files first
        for which in ["lattice", "encap", "surface"]:
            try:
                chunks = self._grpc.download_stl(which)
                fh, path = None, None
                for chunk in chunks:
                    if not path:
                        path = Path(out_dir) / chunk.filename
                        fh = open(path, "wb")
                    fh.write(chunk.data)
                if fh:
                    fh.close()
                    saved.append(str(path))
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"Downloaded: {chunk.filename}")
            except grpc.RpcError:
                pass  # file doesn't exist for this type

        if saved:
            wx.CallAfter(self.m_btnExportSTL.Enable, True)
            wx.CallAfter(self.m_btnViewSTL.Enable, True)
            self._last_stl_paths = saved
            wx.CallAfter(self.m_statusLabel.SetLabel,
                         f"Saved {len(saved)} STL file(s) — opening viewer…")
            wx.CallAfter(self._auto_view_stl)
            return

        # No files found — need to generate first
        wx.CallAfter(self.m_statusLabel.SetLabel,
                     "No STL files found — running gyroid_to_stl.py…")
        try:
            resp = self._grpc.start_stl()
            wx.CallAfter(self.m_statusLabel.SetLabel, f"STL export: {resp.message}")

            # Poll until done
            while True:
                time.sleep(2)
                st = self._grpc.get_stl_status()
                state = pb2.RunStatusResponse.State.Name(st.state)
                wx.CallAfter(self.m_statusLabel.SetLabel, f"Generating STL: {state}")
                if state in ("IDLE", "FINISHED", "CRASHED"):
                    break

            # Now try downloading again
            for which in ["lattice", "encap", "surface"]:
                try:
                    chunks = self._grpc.download_stl(which)
                    fh, path = None, None
                    for chunk in chunks:
                        if not path:
                            path = Path(out_dir) / chunk.filename
                            fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh:
                        fh.close()
                        saved.append(str(path))
                except grpc.RpcError:
                    pass

            wx.CallAfter(self.m_statusLabel.SetLabel,
                         f"Saved {len(saved)} STL file(s)")
            if saved:
                self._last_stl_paths = saved
                wx.CallAfter(self.m_btnViewSTL.Enable, True)
                wx.CallAfter(wx.MessageBox,
                             "STL files saved:\n" + "\n".join(saved),
                             "STL Export", wx.OK | wx.ICON_INFORMATION)
        except Exception as e:
            wx.CallAfter(self.m_statusLabel.SetLabel, f"STL error: {e}")

        wx.CallAfter(self.m_btnExportSTL.Enable, True)

    def onQuadMeshExport(self, event):
        """Open the Quad Mesh → STEP Export dialog."""
        from .GUIwxformbuilder import QuadMeshExportDialog

        dlg = QuadMeshExportDialog(self)

        # Wire up the dialog buttons
        dlg.m_btnRunQuadMesh.Bind(wx.EVT_BUTTON, lambda e: self._qm_run(dlg))
        dlg.m_btnConvertNurbs.Bind(wx.EVT_BUTTON, lambda e: self._qm_nurbs(dlg))
        dlg.m_btnStopQuadMesh.Bind(wx.EVT_BUTTON, lambda e: self._qm_stop(dlg))
        dlg.m_btnViewPyVista.Bind(wx.EVT_BUTTON, lambda e: self._qm_view_pyvista(dlg))
        dlg.m_btnDownloadOBJ.Bind(wx.EVT_BUTTON, lambda e: self._qm_download_obj(dlg))
        dlg.m_btnDownloadSTEP.Bind(wx.EVT_BUTTON, lambda e: self._qm_download_step(dlg))

        dlg.ShowModal()
        dlg.Destroy()

    def _qm_run(self, dlg):
        """Start quad-mesh generation on the server."""
        extra_args = dlg.get_extra_args()
        dlg.m_btnRunQuadMesh.Enable(False)
        dlg.m_btnStopQuadMesh.Enable(True)
        dlg.m_statusQM.SetLabel("Starting quad mesh…")
        dlg.m_txtQMLog.Clear()

        def worker():
            try:
                stub = self._grpc.stub

                # Start quad mesh — exact method from client.py
                resp = stub.StartGyroidToQuadMesh(
                    pb2.QuadMeshRequest(extra_args=extra_args))
                wx.CallAfter(dlg.m_txtQMLog.AppendText,
                             f"Started: {resp.message}\n")
                if not resp.success:
                    wx.CallAfter(dlg.m_statusQM.SetLabel, f"Failed: {resp.message}")
                    wx.CallAfter(dlg.m_btnRunQuadMesh.Enable, True)
                    wx.CallAfter(dlg.m_btnStopQuadMesh.Enable, False)
                    return

                # Stream output — track any ERROR lines
                had_error = False
                try:
                    for line in stub.StreamGyroidToQuadMeshOutput(pb2.Empty()):
                        ts = time.strftime("%H:%M:%S",
                                          time.localtime(line.timestamp_ms / 1000))
                        wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                     f"[{ts}] {line.line}\n")
                        if line.line.startswith("ERROR:"):
                            had_error = True
                except grpc.RpcError:
                    pass

                wx.CallAfter(dlg.m_btnRunQuadMesh.Enable, True)
                wx.CallAfter(dlg.m_btnStopQuadMesh.Enable, False)
                if had_error:
                    wx.CallAfter(dlg.m_statusQM.SetLabel,
                                 "Quad mesh FAILED — see log. "
                                 "Try setting Smoothing iterations to 0 and retry.")
                else:
                    wx.CallAfter(dlg.m_statusQM.SetLabel, "Quad mesh complete.")
                    wx.CallAfter(dlg.m_btnConvertNurbs.Enable, True)
                    wx.CallAfter(dlg.m_btnViewPyVista.Enable, True)
                    wx.CallAfter(dlg.m_btnDownloadOBJ.Enable, True)
                    # Auto-render preview into WebView
                    wx.CallAfter(self._qm_render_preview, dlg)

            except grpc.RpcError as e:
                wx.CallAfter(dlg.m_statusQM.SetLabel,
                             f"Error: {e.details() if hasattr(e,'details') else e}")
                wx.CallAfter(dlg.m_txtQMLog.AppendText, f"\nERROR: {e}\n")
                wx.CallAfter(dlg.m_btnRunQuadMesh.Enable, True)
                wx.CallAfter(dlg.m_btnStopQuadMesh.Enable, False)

        threading.Thread(target=worker, daemon=True).start()

    def _qm_stop(self, dlg):
        try:
            self._grpc.stub.StopGyroidToQuadMesh(pb2.Empty())
            dlg.m_statusQM.SetLabel("Stopped.")
        except Exception as e:
            dlg.m_statusQM.SetLabel(f"Stop error: {e}")

    def _qm_download_obj(self, dlg):
        """Download the OBJ file(s) from the server to outputs/."""
        from pathlib import Path
        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)
        sheets = dlg.get_sheet_selection()
        def worker():
            saved = []
            for sheet in sheets:
                try:
                    chunks = self._grpc.stub.DownloadNurbsFile(
                        pb2.NurbsFileRequest(which=sheet, format="obj"))
                    fh, path = None, None
                    for chunk in chunks:
                        if not path:
                            path = out_dir / chunk.filename
                            fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh:
                        fh.close(); saved.append(str(path))
                except grpc.RpcError as e:
                    wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                 f"Download {sheet} OBJ: {e}\n")
            wx.CallAfter(dlg.m_statusQM.SetLabel,
                         f"OBJ saved to outputs/: {', '.join(saved) if saved else 'none'}")
            if saved:
                self._last_obj_path = saved[0]
        threading.Thread(target=worker, daemon=True).start()

    def _qm_nurbs(self, dlg):
        """Run quad_to_nurbs.py on the server to convert OBJ → STEP."""
        sheets = dlg.get_sheet_selection()
        nurbs_args = dlg.get_nurbs_args()
        dlg.m_btnConvertNurbs.Enable(False)
        dlg.m_statusQM.SetLabel("Converting to NURBS…")

        def worker():
            nurbs_error = False
            for sheet in sheets:
                try:
                    wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                 f"\n── Converting {sheet} sheet to STEP ──\n")
                    resp = self._grpc.stub.StartQuadToNurbs(
                        pb2.QuadToNurbsRequest(which=sheet, extra_args=nurbs_args))
                    wx.CallAfter(dlg.m_txtQMLog.AppendText, f"{resp.message}\n")
                    if not resp.success:
                        nurbs_error = True
                        continue

                    # Stream output — track any ERROR lines
                    try:
                        for line in self._grpc.stub.StreamQuadToNurbsOutput(pb2.Empty()):
                            ts = time.strftime("%H:%M:%S",
                                              time.localtime(line.timestamp_ms / 1000))
                            wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                         f"[{ts}] {line.line}\n")
                            if line.line.startswith("ERROR:"):
                                nurbs_error = True
                    except grpc.RpcError:
                        pass

                except grpc.RpcError as e:
                    wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                 f"NURBS error ({sheet}): {e}\n")
                    nurbs_error = True

            wx.CallAfter(dlg.m_btnConvertNurbs.Enable, True)
            if nurbs_error:
                wx.CallAfter(dlg.m_statusQM.SetLabel,
                             "NURBS conversion FAILED — see log.")
            else:
                wx.CallAfter(dlg.m_statusQM.SetLabel, "NURBS conversion complete.")
                wx.CallAfter(dlg.m_btnDownloadSTEP.Enable, True)

        threading.Thread(target=worker, daemon=True).start()

    def _qm_download_step(self, dlg):
        """Download the STEP file(s) from the server to outputs/."""
        from pathlib import Path
        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)
        sheets = dlg.get_sheet_selection()
        def worker():
            saved = []
            for sheet in sheets:
                try:
                    chunks = self._grpc.stub.DownloadNurbsFile(
                        pb2.NurbsFileRequest(which=sheet, format="step"))
                    fh, path = None, None
                    for chunk in chunks:
                        if not path:
                            path = out_dir / chunk.filename
                            fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh:
                        fh.close(); saved.append(str(path))
                except grpc.RpcError as e:
                    wx.CallAfter(dlg.m_txtQMLog.AppendText,
                                 f"Download {sheet} STEP: {e}\n")
            wx.CallAfter(dlg.m_statusQM.SetLabel,
                         f"STEP saved to outputs/: {', '.join(saved) if saved else 'none'}")
            if saved:
                wx.CallAfter(wx.MessageBox,
                             "STEP files saved:\n" + "\n".join(saved),
                             "STEP Download", wx.OK | wx.ICON_INFORMATION)
        threading.Thread(target=worker, daemon=True).start()

    def _qm_render_preview(self, dlg):
        """Download OBJ to temp dir and render preview into the dialog's WebView."""
        def worker():
            import tempfile
            from pathlib import Path
            tmp_dir = Path(tempfile.mkdtemp())
            saved = []
            for sheet in ["plus", "minus"]:
                try:
                    chunks = self._grpc.stub.DownloadNurbsFile(
                        pb2.NurbsFileRequest(which=sheet, format="obj"))
                    fh, path = None, None
                    for chunk in chunks:
                        if not path:
                            path = tmp_dir / chunk.filename; fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh: fh.close(); saved.append(str(path))
                except grpc.RpcError:
                    pass
            if saved:
                self._last_obj_path = saved[0]
                wx.CallAfter(self._render_mesh_to_webview, saved, dlg.m_webviewQMPreview)
            else:
                wx.CallAfter(dlg.m_statusQM.SetLabel, "Could not download OBJ for preview.")
        threading.Thread(target=worker, daemon=True).start()

    def _render_mesh_to_webview(self, mesh_paths, webview):
        """Render mesh files off-screen and display as image in a WebView."""
        try:
            import pyvista as pv
            import base64, tempfile
            from pathlib import Path

            plotter = pv.Plotter(off_screen=True, window_size=[900, 650])
            body_colors = {
                "lattice": "#4A90D9",   # steel blue
                "encap": "#F5A623",     # amber
                "surface": "#7ED321",   # green
                "plus": "#4A90D9",
                "minus": "#D94A4A",     # red
            }
            body_opacities = {
                "lattice": 1.0,
                "encap": 0.3,           # transparent encapsulation
                "surface": 0.8,
                "plus": 0.9,
                "minus": 0.9,
            }
            for path in mesh_paths:
                try:
                    mesh = pv.read(path)
                    fname = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
                    body = "lattice"
                    for key in body_colors:
                        if key in fname: body = key; break
                    plotter.add_mesh(mesh,
                        color=body_colors.get(body, "#4A90D9"),
                        opacity=body_opacities.get(body, 0.9),
                        show_edges=("quad" in fname or "obj" in fname.split(".")[-1]),
                        edge_color="#888888", line_width=0.3,
                        smooth_shading=True, label=fname)
                except Exception:
                    pass

            plotter.add_axes()
            plotter.set_background("#FAFAFA")
            plotter.camera_position = "iso"

            tmp = Path(tempfile.mktemp(suffix=".png"))
            plotter.screenshot(str(tmp))
            plotter.close()

            b64 = base64.b64encode(tmp.read_bytes()).decode()
            tmp.unlink(missing_ok=True)

            html = (f'<html><body style="margin:0;display:flex;align-items:center;'
                    f'justify-content:center;height:100%;background:#FAFAFA">'
                    f'<img src="data:image/png;base64,{b64}" '
                    f'style="max-width:100%;max-height:100%;object-fit:contain"/>'
                    f'</body></html>')
            webview.SetPage(html, "")
        except ImportError:
            webview.SetPage('<html><body style="display:flex;align-items:center;'
                'justify-content:center;height:100%;color:#999;font-family:sans-serif">'
                '<p>PyVista not installed — pip install pyvista</p></body></html>', "")
        except Exception as e:
            webview.SetPage(f'<html><body style="padding:20px;color:#c00">'
                f'<p>Render error: {e}</p></body></html>', "")

    def _qm_view_pyvista(self, dlg):
        """Open interactive PyVista window (fallback for detailed inspection)."""
        obj_path = getattr(self, "_last_obj_path", None)
        if not obj_path:
            dlg.m_statusQM.SetLabel("No OBJ available yet.")
            return
        try:
            import pyvista as pv
            mesh = pv.read(obj_path)
            plotter = pv.Plotter(title="Quad Mesh — Interactive")
            plotter.add_mesh(mesh, show_edges=True, color="lightblue",
                             edge_color="gray", opacity=0.9)
            plotter.add_axes(); plotter.show_grid()
            plotter.show(interactive=True)
        except ImportError:
            wx.MessageBox("pip install pyvista", "PyVista", wx.OK|wx.ICON_WARNING)
        except Exception as e:
            wx.MessageBox(f"Failed: {e}", "Error", wx.OK|wx.ICON_ERROR)

    def _update_optimizer_plot(self, outer_iterations, webview):
        """Build a multi-subplot Plotly chart — one subplot per metric."""
        if not outer_iterations:
            return

        iters = [d.get("iter", i) for i, d in enumerate(outer_iterations)]
        self._opt_iters = iters

        # Collect available metrics
        all_keys = set()
        for d in outer_iterations:
            all_keys.update(k for k in d.keys() if k != "iter")

        # Prioritised metrics with display names
        metric_config = [
            (["DissPower", "Disspower", "dissPower"], "Dissipation Power (W)"),
            (["meanT", "meantT", "MeanT"], "Mean Temperature (K)"),
            (["gradNorm", "GradNorm"], "Gradient Norm"),
            (["G_oh"], "Overhang Penalty"),
            (["solid_frac"], "Solid Fraction"),
            (["volUse", "Voluse"], "Volume Usage"),
        ]

        # Find which metrics are available
        available = []
        for candidates, label in metric_config:
            for c in candidates:
                if c in all_keys:
                    available.append((c, label))
                    break

        if not available:
            return

        n = len(available)
        traces = []
        for i, (metric, label) in enumerate(available):
            values = [d.get(metric, None) for d in outer_iterations]
            traces.append({
                "x": iters, "y": values,
                "mode": "lines+markers",
                "name": label,
                "xaxis": f"x{i+1}" if i > 0 else "x",
                "yaxis": f"y{i+1}" if i > 0 else "y",
                "marker": {"size": 4},
            })

        # Build subplot layout
        layout = {
            "template": "plotly_white",
            "margin": {"t": 30, "b": 40, "l": 55, "r": 20},
            "showlegend": False,
            "grid": {"rows": n, "columns": 1, "pattern": "independent", "roworder": "top to bottom"},
        }
        for i, (metric, label) in enumerate(available):
            suffix = str(i+1) if i > 0 else ""
            layout[f"xaxis{suffix}"] = {"title": "Iteration" if i == n-1 else ""}
            layout[f"yaxis{suffix}"] = {"title": label}

        webview.SetPage(_plotly_html(traces, layout), "")

    def _auto_view_stl(self):
        """Automatically render STL preview into the results WebView."""
        self._render_mesh_to_webview(self._last_stl_paths, self.m_webviewResults)
        self.m_statusLabel.SetLabel(f"Saved {len(self._last_stl_paths)} STL file(s) — preview rendered.")

    def onViewSTL(self, event):
        """Open interactive PyVista window for detailed STL inspection."""
        paths = getattr(self, "_last_stl_paths", [])
        if not paths:
            wx.MessageBox("Download the STL files first.",
                          "View STL", wx.OK | wx.ICON_INFORMATION)
            return
        self._view_stl_interactive(paths)

    def _view_stl_interactive(self, paths):
        """Open PyVista with per-body toggles and transparency controls."""
        try:
            import pyvista as pv
            plotter = pv.Plotter(title="Heat Exchanger — Interactive Viewer")
            body_colors = {"lattice": "#4A90D9", "encap": "#F5A623", "surface": "#7ED321"}
            body_opacity = {"lattice": 1.0, "encap": 0.3, "surface": 0.8}
            actors = {}
            for path in paths:
                try:
                    mesh = pv.read(path)
                    fname = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    body = "lattice"
                    for key in body_colors:
                        if key in fname.lower(): body = key; break
                    actor = plotter.add_mesh(mesh, show_edges=False,
                        color=body_colors.get(body, "#4A90D9"),
                        opacity=body_opacity.get(body, 1.0),
                        smooth_shading=True, label=fname)
                    actors[body] = actor
                except Exception as e:
                    print(f"Could not load {path}: {e}")
            # Per-body toggle checkboxes
            y_pos = 10
            for body, actor in actors.items():
                def make_toggle(a):
                    def cb(flag): a.SetVisibility(flag)
                    return cb
                plotter.add_checkbox_button_widget(make_toggle(actor), value=True,
                    position=(10, y_pos), size=25,
                    color_on=body_colors.get(body, "#4A90D9"))
                plotter.add_text(body, position=(40, y_pos + 2),
                    font_size=9, color="black")
                y_pos += 35
            plotter.add_axes(); plotter.add_legend()
            plotter.set_background("#FAFAFA")
            plotter.show_grid()
            plotter.show(interactive=True)
        except ImportError:
            wx.MessageBox("pip install pyvista", "PyVista", wx.OK|wx.ICON_WARNING)
        except Exception as e:
            wx.MessageBox(f"Failed: {e}", "PyVista Error", wx.OK|wx.ICON_ERROR)

    def onServerStatus(self, event):
        """Show the current server run status."""
        try:
            resp = self._grpc.get_status()
            state = pb2.RunStatusResponse.State.Name(resp.state)
            wx.MessageBox(
                f"State: {state}\n"
                f"PID: {resp.pid or '—'}\n"
                f"Return code: {resp.return_code}\n"
                f"Message: {resp.message}",
                "Server Status", wx.OK | wx.ICON_INFORMATION)
        except grpc.RpcError as e:
            wx.MessageBox(f"Cannot reach server:\n{e}",
                          "Server Status", wx.OK | wx.ICON_ERROR)

    def onListFiles(self, event):
        """List files on the server and show in a dialog."""
        try:
            resp = self._grpc.stub.ListFiles(pb2.ListFilesRequest(path=""))
            if resp.success:
                file_list = "\n".join(resp.paths[:100])  # limit display
                dlg = wx.TextEntryDialog(self, "Server files (app/):",
                                         "List Files", file_list,
                                         style=wx.OK | wx.TE_MULTILINE)
                dlg.SetSize(500, 400)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                wx.MessageBox(f"Error: {resp.error}", "List Files", wx.OK | wx.ICON_ERROR)
        except grpc.RpcError as e:
            wx.MessageBox(f"Cannot reach server:\n{e}",
                          "List Files", wx.OK | wx.ICON_ERROR)

    def onDownloadApp(self, event):
        """Download the entire app/ folder as a tar.gz."""
        dlg = wx.DirDialog(self, "Save case folder to:")
        if dlg.ShowModal() == wx.ID_OK:
            out_dir = dlg.GetPath()
            self.m_statusLabel.SetLabel("Downloading full case…")

            def worker():
                from pathlib import Path
                try:
                    chunks = self._grpc.stub.DownloadFile(
                        pb2.DownloadRequest(path="", as_tar=True))
                    fh, path = None, None
                    for chunk in chunks:
                        if not path:
                            path = Path(out_dir) / chunk.filename
                            fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh:
                        fh.close()
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"Case saved: {path}")
                    wx.CallAfter(wx.MessageBox,
                                 f"Full case saved:\n{path}",
                                 "Download", wx.OK | wx.ICON_INFORMATION)
                except Exception as e:
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"Download error: {e}")
            threading.Thread(target=worker, daemon=True).start()
        dlg.Destroy()

    def onSyncOptimizedField(self, event):
        """Download the optimised lattice STL from the server and load it into
        the ParaPy viewport.  Also fetches kx/ky/kz for the export wizard.
        """
        obj = self.parapy_obj
        if not obj:
            self.m_statusLabel.SetLabel("No ParaPy object attached.")
            return

        self.m_statusLabel.SetLabel("Downloading optimised STL from server…")

        def worker():
            from pathlib import Path

            # ── 1. Download the lattice STL ──────────────────────────────────
            out_dir = Path("outputs")
            out_dir.mkdir(parents=True, exist_ok=True)
            stl_path = None
            try:
                chunks = self._grpc.download_stl("lattice")
                fh = None
                for chunk in chunks:
                    if fh is None:
                        # use the server-provided filename, saved under outputs/
                        fname = chunk.filename if chunk.filename else "optimized_lattice.stl"
                        stl_path = out_dir / fname
                        fh = open(stl_path, "wb")
                    fh.write(chunk.data)
                if fh:
                    fh.close()
            except Exception as e:
                wx.CallAfter(self.m_statusLabel.SetLabel,
                             f"STL download failed: {e}\n"
                             "Run STL export on the server first (Step 4).")
                return

            if not stl_path or not stl_path.exists():
                wx.CallAfter(self.m_statusLabel.SetLabel,
                             "No STL data received — run the STL export step first.")
                return

            # ── 2. Push path to ParaPy — triggers viewport update ────────────
            abs_path = str(stl_path.resolve())
            try:
                obj.opt_stl_path = abs_path
            except Exception as e:
                wx.CallAfter(self.m_statusLabel.SetLabel,
                             f"ParaPy STL update error: {e}")
                return

            # ── 3. Also fetch kx/ky/kz for export wizard (best-effort) ───────
            try:
                import ast
                import yaml
                resp = self._grpc.stub.GetConfig(pb2.Empty())
                if resp.success:
                    cfg = yaml.safe_load(resp.yaml_content)
                    lat = cfg.get("lattice", {})

                    def _parse(v):
                        if isinstance(v, list):
                            return v
                        if isinstance(v, str) and v.strip():
                            try:
                                return ast.literal_eval(v)
                            except Exception:
                                return []
                        return []

                    kx   = _parse(lat.get("kx_values"))
                    ky   = _parse(lat.get("ky_values"))
                    kz   = _parse(lat.get("kz_values"))
                    ctrl = _parse(lat.get("ctrl_locations"))
                    if kx:
                        obj.opt_kx = kx
                        obj.opt_ky = ky if ky else kx
                        obj.opt_kz = kz if kz else kx
                        if ctrl:
                            obj.opt_ctrl_locations = ctrl
            except Exception:
                pass  # kx/ky/kz sync is best-effort; STL is the primary result

            sz_kb = stl_path.stat().st_size / 1024
            wx.CallAfter(self.m_statusLabel.SetLabel,
                         f"Optimised STL loaded ({sz_kb:.0f} kB) — "
                         f"check 3D viewport (optimized_lattice_stl Part).")

        threading.Thread(target=worker, daemon=True).start()

    def onRunPySLM(self, event):
        """Run PySLM manufacturability analysis on the downloaded STL."""
        paths = getattr(self, "_last_stl_paths", [])
        if not paths:
            wx.MessageBox("Download the STL files first (Export & Download STL button).",
                          "PySLM", wx.OK|wx.ICON_INFORMATION)
            return
        self.m_statusLabel.SetLabel("Running PySLM analysis…")

        def worker():
            try:
                import pyslm
                import pyslm.analysis
                import trimesh
                results = []
                for path in paths:
                    fname = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
                    try:
                        mesh = trimesh.load(path)
                        # Basic mesh quality metrics
                        area = mesh.area
                        volume = mesh.volume if mesh.is_watertight else 0
                        bounds = mesh.bounds
                        size = bounds[1] - bounds[0]
                        results.append(
                            f"── {fname} ──\n"
                            f"  Vertices: {len(mesh.vertices):,}\n"
                            f"  Faces: {len(mesh.faces):,}\n"
                            f"  Surface area: {area:.1f} mm²\n"
                            f"  Volume: {volume:.1f} mm³\n"
                            f"  Watertight: {mesh.is_watertight}\n"
                            f"  Bounding box: {size[0]:.1f} × {size[1]:.1f} × {size[2]:.1f} mm\n"
                        )
                    except Exception as e:
                        results.append(f"── {fname} ──\n  Error: {e}\n")
                report = "\n".join(results)
                wx.CallAfter(self._show_pyslm_report, report)
            except ImportError:
                wx.CallAfter(wx.MessageBox,
                    "PySLM or trimesh not installed.\n\n"
                    "Install with: pip install pyslm trimesh",
                    "PySLM", wx.OK|wx.ICON_WARNING)
            except Exception as e:
                wx.CallAfter(self.m_statusLabel.SetLabel, f"PySLM error: {e}")

        threading.Thread(target=worker, daemon=True).start()

    def _show_pyslm_report(self, report):
        """Show PySLM results in a dialog and save to outputs/pyslm_report.txt."""
        from pathlib import Path
        out_path = Path("outputs") / "pyslm_report.txt"
        Path("outputs").mkdir(exist_ok=True)
        try:
            out_path.write_text(report, encoding="utf-8")
            self.m_statusLabel.SetLabel(f"PySLM report saved: {out_path}")
        except Exception:
            self.m_statusLabel.SetLabel("PySLM analysis complete.")
        dlg = wx.Dialog(self, title="PySLM Manufacturability Report",
                        size=(500, 400), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        sz = wx.BoxSizer(wx.VERTICAL)
        txt = wx.TextCtrl(dlg, value=report, style=wx.TE_MULTILINE|wx.TE_READONLY)
        txt.SetFont(wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        sz.Add(txt, 1, wx.EXPAND|wx.ALL, 10)
        btn = wx.Button(dlg, wx.ID_OK, "Close")
        sz.Add(btn, 0, wx.ALIGN_RIGHT|wx.ALL, 10)
        dlg.SetSizer(sz)
        dlg.ShowModal()
        dlg.Destroy()

    # =================================================================
    # Page 6: Print Preparation (server-side PySLM)
    # =================================================================

    def onRunPrintPrep(self, event):
        """Launch gyroid_print_prep.py on the server and stream its output."""
        extra_args = [
            "--num-workers", str(self.m_spinPPWorkers.GetValue()),
            "--max-bridge-length", f"{self.m_spinPPBridge.GetValue():.3g}",
        ]
        sel = self.m_choicePPBuildDir.GetSelection()
        build_dir = ["z", "x", "y"][sel] if sel < 3 else self.m_txtPPCustomDir.GetValue().strip()
        extra_args += ["--build-direction", build_dir]
        if self.m_chkPPSkipTime.GetValue():
            extra_args.append("--skip-print-time")

        self.m_btnRunPrintPrep.Enable(False)
        self.m_btnStopPrintPrep.Enable(True)
        self.m_btnDownloadBuildSTL.Enable(False)
        self.m_btnDownloadOverhangSTL.Enable(False)
        self.m_btnDownloadSupportsSTL.Enable(False)
        self.m_txtPrintPrepLog.Clear()
        self.m_statusLabel.SetLabel("Starting print preparation…")

        def worker():
            try:
                stub = self._grpc.stub
                resp = stub.StartPrintPrep(pb2.PrintPrepRequest(extra_args=extra_args))
                wx.CallAfter(self.m_txtPrintPrepLog.AppendText,
                             f"args: {' '.join(extra_args)}\nStarted: {resp.message}\n")
                if not resp.success:
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"Print prep failed: {resp.message}")
                    wx.CallAfter(self.m_btnRunPrintPrep.Enable, True)
                    wx.CallAfter(self.m_btnStopPrintPrep.Enable, False)
                    return

                had_error = False
                try:
                    for line in stub.StreamPrintPrepOutput(pb2.Empty()):
                        ts = time.strftime("%H:%M:%S",
                                          time.localtime(line.timestamp_ms / 1000))
                        wx.CallAfter(self.m_txtPrintPrepLog.AppendText,
                                     f"[{ts}] {line.line}\n")
                        if line.line.startswith("ERROR:"):
                            had_error = True
                except grpc.RpcError:
                    pass

                wx.CallAfter(self.m_btnRunPrintPrep.Enable, True)
                wx.CallAfter(self.m_btnStopPrintPrep.Enable, False)
                if had_error:
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 "Print prep FAILED — see log.")
                else:
                    wx.CallAfter(self.m_statusLabel.SetLabel, "Print prep complete.")
                    wx.CallAfter(self.m_btnDownloadBuildSTL.Enable, True)
                    wx.CallAfter(self.m_btnDownloadOverhangSTL.Enable, True)
                    wx.CallAfter(self.m_btnDownloadSupportsSTL.Enable, True)

            except grpc.RpcError as e:
                msg = e.details() if hasattr(e, "details") else str(e)
                wx.CallAfter(self.m_statusLabel.SetLabel, f"Print prep error: {msg}")
                wx.CallAfter(self.m_txtPrintPrepLog.AppendText, f"\nERROR: {e}\n")
                wx.CallAfter(self.m_btnRunPrintPrep.Enable, True)
                wx.CallAfter(self.m_btnStopPrintPrep.Enable, False)

        threading.Thread(target=worker, daemon=True).start()

    def onStopPrintPrep(self, event):
        try:
            self._grpc.stub.StopPrintPrep(pb2.Empty())
            self.m_statusLabel.SetLabel("Print prep stopped.")
        except Exception as e:
            self.m_statusLabel.SetLabel(f"Stop error: {e}")
        self.m_btnStopPrintPrep.Enable(False)
        self.m_btnRunPrintPrep.Enable(True)

    def _pp_download(self, which: str):
        """Download a print-prep output STL (build/overhang/supports) to outputs/."""
        from pathlib import Path
        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)
        self.m_statusLabel.SetLabel(f"Downloading {which} STL…")

        def worker():
            try:
                chunks = self._grpc.stub.DownloadPrintPrepFile(
                    pb2.PrintPrepFileRequest(which=which))
                fh, path = None, None
                for chunk in chunks:
                    if fh is None:
                        path = out_dir / chunk.filename
                        fh = open(path, "wb")
                    fh.write(chunk.data)
                if fh:
                    fh.close()
                    wx.CallAfter(self.m_statusLabel.SetLabel, f"Saved: {path}")
                    wx.CallAfter(self.m_txtPrintPrepLog.AppendText,
                                 f"Downloaded {which} → {path}\n")
                else:
                    wx.CallAfter(self.m_statusLabel.SetLabel,
                                 f"No data received for {which}")
            except grpc.RpcError as e:
                msg = e.details() if hasattr(e, "details") else str(e)
                wx.CallAfter(self.m_statusLabel.SetLabel, f"Download error: {msg}")
                wx.CallAfter(self.m_txtPrintPrepLog.AppendText,
                             f"\nDownload {which} ERROR: {e}\n")

        threading.Thread(target=worker, daemon=True).start()

    def onDownloadBuildSTL(self, event):
        self._pp_download("build")

    def onDownloadOverhangSTL(self, event):
        self._pp_download("overhang")

    def onDownloadSupportsSTL(self, event):
        self._pp_download("supports")

    def onDownloadHistory(self, event):
        """Download full optimization history and save to outputs/history.tsv."""
        from pathlib import Path
        try:
            hist = self._grpc.get_history()
            if not hist.success:
                wx.MessageBox(f"Error: {hist.error}", "History", wx.OK|wx.ICON_ERROR); return
            Path("outputs").mkdir(exist_ok=True)
            path = Path("outputs") / "history.tsv"
            with open(path, "w") as f:
                f.write("\t".join(hist.columns) + "\n")
                for row in hist.rows:
                    parts = []
                    for col in hist.columns:
                        if col in row.values:
                            v = row.values[col]
                            parts.append("nan" if math.isnan(v) else f"{v:g}")
                        elif col in row.strings:
                            parts.append(row.strings[col])
                        else:
                            parts.append("")
                    f.write("\t".join(parts) + "\n")
            self.m_statusLabel.SetLabel(f"History saved: {path}")
        except grpc.RpcError as e:
            wx.MessageBox(f"gRPC error: {e.details()}", "History", wx.OK|wx.ICON_ERROR)
