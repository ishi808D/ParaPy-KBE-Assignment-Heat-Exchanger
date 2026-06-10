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

        self._grpc = GrpcConnection(
            host=getattr(parapy_obj, "grpc_host", "localhost"),
            port=getattr(parapy_obj, "grpc_port", 50051))

        for wv in [self.m_webviewSE, self.m_webviewBaseline,
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
            (self.m_spinSizeX,     "enc_length",          0.10, 1000),
            (self.m_spinSizeY,     "enc_width",           0.05, 1000),
            (self.m_spinSizeZ,     "enc_height",          0.05, 1000),
            (self.m_spinEncapWall, "enc_wall_thickness",  0.002, 1000),
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

        # kinematic viscosity and density come from the fluid Part
        try:
            self.m_spinNu.SetValue(obj.fluid.kinematic_viscosity)
            self.m_spinRhoFluid.SetValue(obj.fluid.density)
        except Exception:
            self.m_spinNu.SetValue(1e-6)
            self.m_spinRhoFluid.SetValue(1000.0)

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
            try: setattr(obj, attr, spinner.GetValue() / scale)
            except Exception: pass

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

        NOTE: geometry.size_mm, geometry.cells, and inlet/outlet window
        coordinates are NOT pushed — the server's blockMeshDict template
        is fixed at 100mm and those values must stay consistent with the
        mesh. Only flow/thermal/optimization params are pushed.
        Clarify with Huirne before enabling geometry overrides.
        """
        p = {}

        # ── Safe to push: flow & thermal ──
        p["inlet.velocity_magnitude"] = self.m_spinInletVel.GetValue()
        p["inlet.temperature"] = self.m_spinInletTemp.GetValue()
        p["outlet.pressure"] = self.m_spinOutletP.GetValue()

        p["material.Texterior"] = self.m_spinTexterior.GetValue()
        p["material.nu"] = self.m_spinNu.GetValue()
        p["material.rho_fluid"] = self.m_spinRhoFluid.GetValue()
        p["thermal.initial_temperature"] = self.m_spinTinitial.GetValue()

        # ── Safe to push: optimization ──
        mode = "pressure" if self.m_radioMode.GetSelection() == 0 else "heat"
        p["optimization.mode"] = mode
        p["optimization.meantT_max"] = self.m_spinMeanTMax.GetValue()
        p["optimization.dissPower_max"] = self.m_spinDissPMax.GetValue()
        p["optimization.wall"] = int(self.m_spinWallCells.GetValue())
        p["optimization.unit"] = int(self.m_spinUnitCells.GetValue())
        p["optimization.am_theta"] = self.m_spinAmTheta.GetValue()
        p["optimization.no_overhang"] = self.m_chkNoOverhang.GetValue()
        p["optimization.kbound"] = self.m_spinKbound.GetValue()

        # ── Safe to push: run control ──
        p["run.iters"] = int(self.m_spinMaxIter.GetValue())

        # ── NOT pushed (mesh-dependent, leave server defaults): ──
        # geometry.size_mm, geometry.cells, geometry.flow_axis,
        # geometry.encap_wall_mm, inlet.window_origin_mm,
        # inlet.window_size_mm, outlet.window_origin_mm,
        # outlet.window_size_mm

        return p

    # =================================================================
    # Navigation
    # =================================================================

    def _go_to(self, idx):
        idx = max(0, min(idx, self.NUM_PAGES - 1))
        self._page = idx
        self.m_simplebook.ChangeSelection(idx)
        self.m_headerLabel.SetLabel(self.PAGE_TITLES[idx])
        self._update_nav()

    def _update_nav(self):
        self.m_btnBack.Enable(self._page > 0)
        self.m_btnNext.SetLabel("Finish" if self._page == self.NUM_PAGES - 1 else "Next ▶")

    def onBack(self, event): self._go_to(self._page - 1)

    def onNext(self, event):
        if self._page == self.NUM_PAGES - 1:
            self.Close(); return
        if self._page == 0:
            self._write_gui_to_parapy()
            self._compute_sizing()
        elif self._page == 3:
            self._write_gui_to_parapy()
        self._go_to(self._page + 1)

    # =================================================================
    # Page 0: Apply geometry
    # =================================================================

    def onApplyGeom(self, event):
        self._write_gui_to_parapy()
        self.m_statusLabel.SetLabel("Applied to ParaPy model.")

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
        self.m_statusLabel.SetLabel("Pushing config & starting baseline…")
        self.m_gaugeBaseline.SetValue(0)
        self._stop.clear()
        threading.Thread(target=self._run_worker, args=("baseline",), daemon=True).start()

    # =================================================================
    # Page 4: Optimization (real gRPC)
    # =================================================================

    def onStartOpt(self, event):
        self.m_btnStartOpt.Enable(False)
        self.m_statusLabel.SetLabel("Pushing config & starting optimization…")
        self._opt_iters.clear(); self._opt_objs.clear(); self._opt_cstrs.clear()
        self._stop.clear()
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
            # 1) Push config
            patch = self._build_config_patch()
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
        self.m_txtBaseDissip.SetValue(f"{dissip:.2f}")
        self.m_txtBaseMeanT.SetValue(f"{meanT:.2f}")
        self.m_btnRunBaseline.Enable(True)
        self.m_statusLabel.SetLabel("Baseline complete.")
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
        self.m_statusLabel.SetLabel("Optimization complete.")
        if self.parapy_obj:
            try:
                self.parapy_obj.opt_dissipation = dissip
                self.parapy_obj.opt_mean_temp = meanT
            except Exception: pass

    def _worker_error(self, mode, msg):
        self.m_statusLabel.SetLabel(f"{mode} failed: {msg}")
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
        self.m_statusLabel.SetLabel("Starting STL export…")
        threading.Thread(target=self._stl_worker, daemon=True).start()

    def _stl_worker(self):
        try:
            resp = self._grpc.start_stl()
            wx.CallAfter(self.m_statusLabel.SetLabel, f"STL: {resp.message}")
            while True:
                time.sleep(2)
                st = self._grpc.get_stl_status()
                state = pb2.RunStatusResponse.State.Name(st.state)
                wx.CallAfter(self.m_statusLabel.SetLabel, f"STL: {state}")
                if state in ("IDLE", "FINISHED", "CRASHED"): break
            from pathlib import Path
            out = Path(".")
            for which in ["lattice", "encap"]:
                try:
                    chunks = self._grpc.download_stl(which)
                    fh, path = None, None
                    for chunk in chunks:
                        if not path: path = out / chunk.filename; fh = open(path, "wb")
                        fh.write(chunk.data)
                    if fh: fh.close()
                    wx.CallAfter(self.m_statusLabel.SetLabel, f"Saved: {path}")
                except grpc.RpcError:
                    pass
        except Exception as e:
            wx.CallAfter(self.m_statusLabel.SetLabel, f"STL error: {e}")

    def onRunPySLM(self, event):
        wx.MessageBox("PySLM analysis — connect to downloaded STL.", "PySLM", wx.OK|wx.ICON_INFORMATION)

    def onExportSTEP(self, event):
        obj = self.parapy_obj
        if obj and hasattr(obj, "step_writer"):
            try: obj.step_writer.write(); wx.MessageBox("STEP written.", "OK", wx.OK|wx.ICON_INFORMATION)
            except Exception as e: wx.MessageBox(f"Failed: {e}", "Error", wx.OK|wx.ICON_ERROR)
        else:
            wx.MessageBox("No step_writer on model.", "STEP", wx.OK|wx.ICON_WARNING)

    def onDownloadHistory(self, event):
        """Download full optimization history and save as TSV."""
        try:
            hist = self._grpc.get_history()
            if not hist.success:
                wx.MessageBox(f"Error: {hist.error}", "History", wx.OK|wx.ICON_ERROR); return
            dlg = wx.FileDialog(self, "Save history", wildcard="TSV files (*.tsv)|*.tsv",
                                style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            if dlg.ShowModal() == wx.ID_OK:
                path = dlg.GetPath()
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
            dlg.Destroy()
        except grpc.RpcError as e:
            wx.MessageBox(f"gRPC error: {e.details()}", "History", wx.OK|wx.ICON_ERROR)
