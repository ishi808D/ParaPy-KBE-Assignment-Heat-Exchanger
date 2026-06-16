"""
heat_exchanger.py
-----------------
Root class of the Bio-Inspired Heat Exchanger KBE application.

Maps to UML class: **HeatExchanger**

The ParaPy product tree mirrors the UML:

    HeatExchanger  (root — this class)
    ├── loader              Loader            (JSON / Excel input)
    ├── encapsulation       Encapsulation     (3-D CAD)
    ├── environment         HeatExchangerEnv  (boundary conditions)
    ├── fluid               FluidElement      (coolant properties)
    ├── lattice             LatticeFormulation(TPMS field + material)
    ├── objectives          Objectives        (optimiser target)
    ├── manufacturing       ManufacturingConstraintSet
    ├── sizing              SemiEmpirical     (Femmer correlations)
    ├── sim                 SimulationConnector (gRPC bridge)
    └── exporter            GeometryExportService

Workflow (fire these from the GUI property grid)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
1.  Tweak inputs → encapsulation geometry updates live.
2.  Fire ``start_baseline()`` → patches config, runs one OpenFOAM case.
3.  Fire ``start_optimisation()`` → full MTO loop with adjoint solver.
4.  Fire ``export_stl()`` → trigger server-side STL export + download.
5.  Fire ``export_step()`` → encapsulation shell → STEP file.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from parapy.core import Input, Attribute, Part, action
from parapy.geom import GeomBase

from .encapsulation import Encapsulation
from .environment import HeatExchangerEnvironment
from .fluid import FluidElement
from .lattice import LatticeFormulation, TPMSFrequencyField
from .objectives import Objectives, ManufacturingConstraintSet
from .solidity import SemiEmpirical
from .simulation import SimulationConnector
from .geometry_export import GeometryExportService
from .loader import Loader
from .validators import validate_heat_exchanger
from .gyroid import GyroidMesh
from .manufacturability import ManufacturabilityAnalysis
from .pyslm_analysis import PySLMAnalysis
from .optimization_history import OptimizationHistory
from .reporting import ReportGenerator


class HeatExchanger(GeomBase):
    """Top-level KBE object.  Instantiate and pass to ``display()``."""

    # ═════════════════════════════════════════════════════════════════
    # User-facing inputs  (shown in the ParaPy property grid)
    # ═════════════════════════════════════════════════════════════════

    # ── file paths ───────────────────────────────────────────────────

    json_path: str = Input("inputs/requirements.json")
    xlsx_path: str = Input("inputs/materials.xlsx")

    # ── encapsulation geometry  [m] ──────────────────────────────────

    enc_length:        float = Input(0.10)
    enc_width:         float = Input(0.05)
    enc_height:        float = Input(0.05)
    enc_wall_thickness:float = Input(0.002)
    inlet_bore_width:  float = Input(0.010)
    inlet_bore_height: float = Input(0.015)
    outlet_bore_width: float = Input(0.010)
    outlet_bore_height: float = Input(0.015)
    tube_wall:         float = Input(0.001)
    tube_length:       float = Input(0.020)

    # ── environment ──────────────────────────────────────────────────

    inflow_velocity:       float = Input(1.0)
    inflow_temperature:    float = Input(350.0)
    outlet_pressure:       float = Input(101325.0)
    exterior_temperature:  float = Input(293.15)
    wall_heat_conduction:  float = Input(10.0)
    mech_dissipation_lower:float = Input(0.0)
    mech_dissipation_upper:float = Input(10.0)

    # ── lattice ──────────────────────────────────────────────────────

    tpms_type:           str   = Input("gyroid")

    #: Initial uniform wavenumber for the baseline simulation  [rad/m].
    #: 2π/k = unit-cell size, so k=628 → 10 mm cells (≈10 cells per 100 mm box).
    initial_wavenumber:  float = Input(628.0)

    #: iso-level controlling the gyroid wall thickness / solidity
    iso_level:           float = Input(0.3)

    #: voxel resolution for the live gyroid preview (keep ≤ 70 for speed)
    preview_resolution:  int   = Input(60)

    #: voxel resolution for the final STL export (higher = finer)
    export_resolution:   int   = Input(150)

    # ── objectives ───────────────────────────────────────────────────

    optimizer_mode:     str   = Input("minimize_outlet_temperature")
    target_nusselt:     float = Input(10.0)
    operating_reynolds: float = Input(1000.0)

    # ── manufacturing ────────────────────────────────────────────────

    min_feature_size:   float = Input(2e-4)
    max_overhang_angle: float = Input(45.0)
    build_volume:       tuple = Input((0.25, 0.25, 0.30))

    # ── gRPC connection ──────────────────────────────────────────────

    grpc_host: str = Input("localhost")
    grpc_port: int = Input(50051)

    # ── server config: optimization  (maps to optimization.* in YAML) ─

    meantT_max:      float = Input(340.0,     label="Mean T constraint (K)")
    dissPower_max:   float = Input(2800000.0, label="Dissipation constraint (W)")
    opt_wall_cells:  int   = Input(6,         label="Wall thickness (cells)")
    opt_unit_cells:  int   = Input(75,        label="Unit cell size (cells)")
    am_theta:        float = Input(45.0,      label="Overhang angle (deg)")
    max_iterations:  int   = Input(100,       label="Max iterations")
    kbound:          float = Input(0.08,      label="kbound")
    no_overhang:     bool  = Input(False,     label="Enable overhang constraint")
    opt_mode:        str   = Input("pressure", label="Opt mode (pressure/heat)")

    # ── results (written back by the workflow wizard) ─────────────────

    baseline_dissipation: float = Input(0.0, label="Baseline Dissipation (W)")
    baseline_mean_temp:   float = Input(0.0, label="Baseline Mean Temp (K)")
    opt_dissipation:      float = Input(0.0, label="Opt Dissipation (W)")
    opt_mean_temp:        float = Input(0.0, label="Opt Mean Temp (K)")

    # ── optimised wavenumber field (synced from server after CFD run) ──
    # Empty list = not yet synced; gyroid_preview falls back to uniform baseline.

    opt_ctrl_locations: list = Input([], label="Optimised ctrl-point locations (m)")
    opt_kx: list = Input([], label="Optimised kx field (rad/m) per ctrl point")
    opt_ky: list = Input([], label="Optimised ky field (rad/m) per ctrl point")
    opt_kz: list = Input([], label="Optimised kz field (rad/m) per ctrl point")

    # ═════════════════════════════════════════════════════════════════
    # Parts  (product tree)
    # ═════════════════════════════════════════════════════════════════

    @Part
    def loader(self):
        return Loader(
            json_path=self.json_path,
            xlsx_path=self.xlsx_path,
        )

    @Part
    def encapsulation(self):
        return Encapsulation(
            length=self.enc_length,
            width=self.enc_width,
            height=self.enc_height,
            wall_thickness=self.enc_wall_thickness,
            inlet_bore_width=self.inlet_bore_width,
            inlet_bore_height=self.inlet_bore_height,
            outlet_bore_width=self.outlet_bore_width,
            outlet_bore_height=self.outlet_bore_height,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            position=self.position,
        )

    @Part
    def environment(self):
        return HeatExchangerEnvironment(
            inflow_velocity=self.inflow_velocity,
            inflow_temperature=self.inflow_temperature,
            outlet_pressure=self.outlet_pressure,
            exterior_temperature=self.exterior_temperature,
            wall_heat_conduction=self.wall_heat_conduction,
            mech_dissipation_lower=self.mech_dissipation_lower,
            mech_dissipation_upper=self.mech_dissipation_upper,
        )

    @action(label="Open Workflow Wizard")
    def edit_environment(self):
        import wx
        from .workflow import WorkflowWizard
        app = wx.GetApp()
        parent = app.GetTopWindow()
        frm = WorkflowWizard(parent, parapy_obj=self)
        frm.Show()
        return "Workflow wizard opened."


    @Part
    def fluid(self):
        return FluidElement()

    @Part
    def lattice(self):
        return LatticeFormulation(
            tpms_type=self.tpms_type,
            _default_ctrl=self._ctrl_points,
            _default_k=[self.initial_wavenumber] * len(self._ctrl_points),
        )

    @Part
    def objectives(self):
        return Objectives(
            mode=self.optimizer_mode,
            target_nusselt=self.target_nusselt,
            operating_reynolds=self.operating_reynolds,
        )

    @Part
    def manufacturing(self):
        return ManufacturingConstraintSet(
            min_feature_size=self.min_feature_size,
            max_overhang_angle=self.max_overhang_angle,
            build_volume=self.build_volume,
        )

    @Part
    def sizing(self):
        return SemiEmpirical(
            hydraulic_diameter=self.encapsulation.hydraulic_diameter,
            inflow_velocity=self.inflow_velocity,
            kinematic_viscosity=self.fluid.kinematic_viscosity,
            fluid_conductivity=self.fluid.conductivity,
            prandtl_number=self.fluid.prandtl_number,
            target_nusselt=self.target_nusselt,
            operating_re=self.operating_reynolds,
            simulation_re=self.reynolds_number,
        )

    @Part
    def sim(self):
        return SimulationConnector(
            host=self.grpc_host,
            port=self.grpc_port,
        )

    @Part
    def exporter(self):
        return GeometryExportService(
            output_dir="outputs",
            output_name="heat_exchanger",
        )

    @Part
    def gyroid_preview(self):
        """Live TPMS gyroid mesh for the current design point.

        Uses the optimised kx/ky/kz field (opt_kx/ky/kz inputs) when it has
        been synced from the server, otherwise falls back to the uniform
        initial_wavenumber baseline.  Solidity, mass and surface area are
        read straight off this mesh.
        """
        return GyroidMesh(
            length=self.enc_length - 2 * self.enc_wall_thickness,
            width=self.enc_width - 2 * self.enc_wall_thickness,
            height=self.enc_height - 2 * self.enc_wall_thickness,
            ctrl_locations=self._eff_ctrl,
            kx=self._eff_kx,
            ky=self._eff_ky,
            kz=self._eff_kz,
            tpms_type=self.tpms_type,
            iso_level=self.iso_level,
            resolution=self.preview_resolution,
            material_density=self.lattice.material.density,
        )

    @Part
    def manufacturability(self):
        """DfAM overhang + wall-thickness penalty on the preview mesh."""
        return ManufacturabilityAnalysis(
            face_normals=self.gyroid_preview.face_normals,
            face_areas=self.gyroid_preview.face_areas,
            solidity=self.gyroid_preview.solidity,
            unit_cell_size=self.lattice.frequency_field.mean_unit_cell_size,
            max_overhang_angle=self.max_overhang_angle,
            min_feature_size=self.min_feature_size,
        )

    @Part
    def pyslm(self):
        """Final DfAM analysis on the exported STL (optional dependency)."""
        return PySLMAnalysis(
            stl_path="outputs/heat_exchanger_lattice.stl",
            max_overhang_angle=self.max_overhang_angle,
        )

    @Part
    def history(self):
        """Optimisation history parser (populated after a run)."""
        return OptimizationHistory(raw_history="")

    @Part
    def report(self):
        """Design-summary PDF + convergence plot generator."""
        return ReportGenerator(
            output_dir="outputs",
            report_name="design_report",
            design_summary=self.design_summary,
            history=self.history,
        )


    # ═════════════════════════════════════════════════════════════════
    # Key attributes
    # ═════════════════════════════════════════════════════════════════

    @Attribute
    def reynolds_number(self) -> float:
        """Re at the laminar simulation inlet conditions."""
        dh = self.encapsulation.hydraulic_diameter
        return self.inflow_velocity * dh / self.fluid.kinematic_viscosity

    @Attribute
    def _eff_ctrl(self):
        """Effective ctrl-point locations: optimised if available, else baseline 2×2×2 grid."""
        return self.opt_ctrl_locations if self.opt_ctrl_locations else self._ctrl_points

    @Attribute
    def _eff_kx(self):
        """Effective kx field: optimised if available, else uniform initial_wavenumber."""
        return self.opt_kx if self.opt_kx else [self.initial_wavenumber] * len(self._ctrl_points)

    @Attribute
    def _eff_ky(self):
        """Effective ky field: optimised if available, else uniform initial_wavenumber."""
        return self.opt_ky if self.opt_ky else [self.initial_wavenumber] * len(self._ctrl_points)

    @Attribute
    def _eff_kz(self):
        """Effective kz field: optimised if available, else uniform initial_wavenumber."""
        return self.opt_kz if self.opt_kz else [self.initial_wavenumber] * len(self._ctrl_points)

    @Attribute
    def _ctrl_points(self) -> list[tuple[float, float, float]]:
        """2×2×2 grid of RBF control points inside the interior cavity."""
        t = self.enc_wall_thickness
        il = self.enc_length - 2*t
        iw = self.enc_width  - 2*t
        ih = self.enc_height - 2*t
        return [
            (t + fx * il, t + fy * iw, t + fz * ih)
            for fx in (0.25, 0.75)
            for fy in (0.25, 0.75)
            for fz in (0.25, 0.75)
        ]

    @Attribute
    def validation_errors(self) -> list[str]:
        """Cross-parameter validation.  Empty list = all OK."""
        return validate_heat_exchanger(self)

    @Attribute
    def is_valid(self) -> bool:
        return len(self.validation_errors) == 0

    @Attribute
    def design_summary(self) -> dict:
        """Complete design summary for the PDF report."""
        enc = self.encapsulation
        return {
            "encapsulation": {
                "length_mm": round(enc.length * 1e3, 2),
                "width_mm":  round(enc.width * 1e3, 2),
                "height_mm": round(enc.height * 1e3, 2),
                "wall_mm":   round(enc.wall_thickness * 1e3, 2),
                "Dh_mm":     round(enc.hydraulic_diameter * 1e3, 3),
                "V_int_cm3": round(enc.interior_volume * 1e6, 3),
            },
            "flow": {
                "v_in_m_s":  self.inflow_velocity,
                "T_in_K":    self.inflow_temperature,
                "p_out_Pa":  self.outlet_pressure,
                "Re":        round(self.reynolds_number, 1),
                "Pr":        round(self.fluid.prandtl_number, 3),
            },
            "sizing": self.sizing.summary,
            "lattice": {
                "tpms":      self.tpms_type,
                "k0_rad_m":  self.initial_wavenumber,
                "uc_mm":     round(self.lattice.frequency_field.mean_unit_cell_size * 1e3, 2),
                "phi":       round(self.sizing.required_solidity, 4),
            },
            "preview_geometry": {
                "solidity":       round(self.gyroid_preview.solidity, 4),
                "mass_g":         round(self.gyroid_preview.mass * 1e3, 2),
                "surface_cm2":    round(self.gyroid_preview.surface_area * 1e4, 1),
                "n_triangles":    self.gyroid_preview.n_triangles,
            },
            "manufacturability": self.manufacturability.summary,
        }

    # ═════════════════════════════════════════════════════════════════
    # Actions  (fire from GUI: right-click → Evaluate)
    # ═════════════════════════════════════════════════════════════════

    def _push_config(self) -> None:
        """Merge all inputs into a config patch and push to gRPC server.

        Keys match the actual gyroid_case_config.yaml structure.
        Geometry is pushed from the current enclosure dimensions so STL,
        quad mesh, and optimization runs all use the edited model rather
        than whatever geometry happened to be active on the server.
        """
        cfg: dict = {}

        # geometry
        cfg["geometry.length"] = self.enc_length
        cfg["geometry.width"] = self.enc_width
        cfg["geometry.height"] = self.enc_height
        cfg["geometry.wall_thickness"] = self.enc_wall_thickness

        # inlet
        cfg["inlet.velocity_magnitude"] = self.inflow_velocity
        cfg["inlet.temperature"] = self.inflow_temperature

        # outlet
        cfg["outlet.pressure"] = self.outlet_pressure

        # material / thermal
        cfg["material.Texterior"] = self.exterior_temperature
        cfg["material.nu"] = self.fluid.kinematic_viscosity
        cfg["thermal.initial_temperature"] = self.exterior_temperature

        # optimization
        cfg["optimization.mode"] = self.opt_mode
        cfg["optimization.meantT_max"] = self.meantT_max
        cfg["optimization.dissPower_max"] = self.dissPower_max
        cfg["optimization.wall"] = self.opt_wall_cells
        cfg["optimization.unit"] = self.opt_unit_cells
        cfg["optimization.am_theta"] = self.am_theta
        cfg["optimization.no_overhang"] = self.no_overhang
        cfg["optimization.kbound"] = self.kbound

        # run
        cfg["run.iters"] = self.max_iterations

        # also include sub-part patches if they provide them
        for part_name in ("environment", "lattice", "objectives", "manufacturing"):
            part = getattr(self, part_name, None)
            if part and hasattr(part, "grpc_patch_dict"):
                cfg.update(part.grpc_patch_dict)

        self.sim.patch_config(cfg)

    def start_baseline(self) -> str:
        """Push config and launch a single (non-optimised) OpenFOAM run."""
        if not self.is_valid:
            raise ValueError(
                "Validation failed:\n" + "\n".join(self.validation_errors)
            )
        self._push_config()
        return self.sim.start()

    def start_optimisation(self) -> str:
        """Push config and launch the full MTO optimisation loop."""
        if not self.is_valid:
            raise ValueError(
                "Validation failed:\n" + "\n".join(self.validation_errors)
            )
        self._push_config()
        return self.sim.start(extra_args=["--optimise"])

    def stop_simulation(self) -> str:
        """Stop whatever is running on the server."""
        return self.sim.stop()

    def export_stl(self, which: str = "lattice") -> str:
        """Trigger server-side STL export and download the file."""
        self.sim.trigger_stl_export()
        return self.sim.download_stl(which=which, out_dir="outputs")

    def export_step(self) -> str:
        """Export the encapsulation shell as a STEP file."""
        return self.exporter.write_assembly(self.encapsulation.shell)

    def export_lattice_stl(self, high_res: bool = True) -> str:
        """Write the locally-generated gyroid lattice to STL.

        Uses the optimised kx/ky/kz field when available (synced via wizard
        "Sync Opt Field" button), otherwise the uniform baseline wavenumber.
        Uses ``export_resolution`` when ``high_res`` is True (slow, fine),
        otherwise the live preview resolution.  Returns the file path.
        """
        if high_res:
            mesh = GyroidMesh(
                length=self.enc_length - 2 * self.enc_wall_thickness,
                width=self.enc_width - 2 * self.enc_wall_thickness,
                height=self.enc_height - 2 * self.enc_wall_thickness,
                ctrl_locations=self._eff_ctrl,
                kx=self._eff_kx,
                ky=self._eff_ky,
                kz=self._eff_kz,
                tpms_type=self.tpms_type,
                iso_level=self.iso_level,
                resolution=self.export_resolution,
                material_density=self.lattice.material.density,
            )
        else:
            mesh = self.gyroid_preview
        return mesh.write_stl("outputs/heat_exchanger_lattice.stl")

    def refresh_history(self) -> int:
        """Pull the latest optimisation history from the server.

        Returns the number of iterations recorded.
        """
        self.history.raw_history = self.sim.optimisation_history
        return self.history.n_iterations

    def run_pyslm(self) -> dict:
        """Run the PySLM DfAM analysis on the exported lattice STL."""
        return self.pyslm.report

    def generate_report(self) -> str:
        """Generate the design-summary PDF (and convergence plots)."""
        self.report.generate_convergence_png()
        return self.report.generate()
    
    

    # ── class-method loaders ─────────────────────────────────────────

    @classmethod
    def from_json(cls, path: str) -> "HeatExchanger":
        """Instantiate from a requirements JSON file.

        Unknown keys are silently ignored so the JSON can contain
        comments (keys starting with ``_``).
        """
        with open(path) as f:
            raw = json.load(f)
        known = {s.name for s in cls.__slots__}
        data = {k: v for k, v in raw.items()
                if not k.startswith("_") and k in known}
        return cls(**data)


    # ═════════════════════════════════════════════════════════════════
    # Semi-empirical sizing attributes  (used by workflow wizard)
    # Uses EXISTING inputs: inflow_velocity, enc_width, enc_height,
    # enc_length, and self.fluid / self.encapsulation Parts.
    # ═════════════════════════════════════════════════════════════════

    @Attribute
    def hydraulic_diameter(self):
        """Hydraulic diameter of the interior cavity (m)."""
        return self.encapsulation.hydraulic_diameter

    @Attribute
    def solidity(self):
        """Required solidity from semi-empirical correlation.
        TODO: Replace with actual gyroid fits from DOI 10.1016/j.enconman.2023.116955
        """
        Re = self.reynolds_number
        Pr = self.fluid.prandtl_number
        base = 0.023 * Re**0.8 * Pr**0.4
        target_Nu = 0.5 * base * (1 + 2.5 * 0.3)
        if base == 0:
            return 0.3
        return max(0.05, min(0.95, (target_Nu / base - 1.0) / 2.5))

    @Attribute
    def nusselt_number(self):
        """Nusselt number from semi-empirical correlation."""
        return 0.023 * self.reynolds_number**0.8 * self.fluid.prandtl_number**0.4 * (1 + 2.5 * self.solidity)

    @Attribute
    def friction_factor(self):
        """Friction factor from semi-empirical correlation."""
        return (64.0 / max(self.reynolds_number, 1)) * (1 + 10 * self.solidity)

    @Attribute
    def pressure_drop(self):
        """Estimated pressure drop (Pa)."""
        L = self.enc_length
        D_h = self.hydraulic_diameter
        rho = self.fluid.density
        U = self.inflow_velocity
        return self.friction_factor * (L / D_h) * 0.5 * rho * U**2 if D_h > 0 else 0.0