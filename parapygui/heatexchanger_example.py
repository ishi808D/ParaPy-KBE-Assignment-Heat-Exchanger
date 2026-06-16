# -*- coding: utf-8 -*-
"""
heatexchanger_example.py

Minimal example showing how the workflow wizard integrates
with a ParaPy class via @action.

The HeatExchanger class is the DATA BACKBONE:
  - @Input  = user-editable parameters (show in property grid)
  - @Attribute = computed values (derived from inputs)
  - @Part = geometry (rendered in 3D viewport)
  - @action = buttons in the GUI (one launches the wizard)

The wizard READS from and WRITES BACK TO this object.
"""

import math
from parapy.core import Base, Input, Attribute, Part, action
from parapy.geom import GeomBase, Box


class HeatExchanger(GeomBase):
    """Top-level ParaPy class for the bio-inspired heat exchanger."""

    # ── Geometry inputs (editable in property grid AND in wizard) ──
    enc_length_x: float = Input(100.0, label="Enclosure X (mm)")
    enc_length_y: float = Input(100.0, label="Enclosure Y (mm)")
    enc_length_z: float = Input(100.0, label="Enclosure Z (mm)")

    # ── Boundary conditions ──
    inlet_temperature: float = Input(350.0, label="Inlet Temperature (K)")
    inlet_flow_rate: float = Input(0.5, label="Inlet Flow Rate (kg/s)")
    outlet_pressure: float = Input(101325.0, label="Outlet Pressure (Pa)")
    wall_temperature: float = Input(400.0, label="Wall Temperature (K)")

    # ── Optimizer settings (written by wizard page 3) ──
    opt_mode: int = Input(0, label="Opt Mode (0=min T, 1=min dissip)")
    constraint_bound: float = Input(10.0, label="Constraint Bound")
    min_wall_thickness: float = Input(0.4, label="Min Wall Thickness (mm)")
    max_overhang_angle: float = Input(45.0, label="Max Overhang (deg)")
    max_iterations: int = Input(200, label="Max Iterations")

    # ── Results (written back by wizard after simulation) ──
    baseline_dissipation: float = Input(0.0, label="Baseline Dissipation (W)")
    baseline_outlet_temp: float = Input(0.0, label="Baseline Outlet Temp (K)")
    opt_dissipation: float = Input(0.0, label="Opt Dissipation (W)")
    opt_outlet_temp: float = Input(0.0, label="Opt Outlet Temp (K)")

    # ==================================================================
    # Computed attributes (semi-empirical relations)
    # ==================================================================

    @Attribute
    def fluid_density(self):
        """Air density from ideal gas law (kg/m³)."""
        return self.outlet_pressure / (287.0 * self.inlet_temperature)

    @Attribute
    def cross_section_area(self):
        """Flow cross-section (m²)."""
        return (self.enc_length_y / 1000.0) * (self.enc_length_z / 1000.0)

    @Attribute
    def bulk_velocity(self):
        """Bulk velocity (m/s)."""
        A = self.cross_section_area
        return self.inlet_flow_rate / (self.fluid_density * A) if A > 0 else 1.0

    @Attribute
    def hydraulic_diameter(self):
        """Hydraulic diameter (m)."""
        return 2.0 * min(self.enc_length_y, self.enc_length_z) / 1000.0

    @Attribute
    def reynolds_number(self):
        """Reynolds number."""
        mu = 2.0e-5  # dynamic viscosity (Pa·s)
        return self.fluid_density * self.bulk_velocity * self.hydraulic_diameter / mu

    @Attribute
    def solidity(self):
        """Required solidity from semi-empirical correlation.
        TODO: Replace with real curve-fit from DOI 10.1016/j.enconman.2023.116955
        """
        Re = self.reynolds_number
        Pr = 0.71
        base = 0.023 * Re**0.8 * Pr**0.4
        target_Nu = 0.5 * base * (1 + 2.5 * 0.3)
        if base == 0:
            return 0.3
        return max(0.05, min(0.95, (target_Nu / base - 1.0) / 2.5))

    @Attribute
    def nusselt_number(self):
        """Nusselt number from semi-empirical correlation."""
        return 0.023 * self.reynolds_number**0.8 * 0.71**0.4 * (1 + 2.5 * self.solidity)

    @Attribute
    def friction_factor(self):
        """Friction factor from semi-empirical correlation."""
        return (64.0 / max(self.reynolds_number, 1)) * (1 + 10 * self.solidity)

    @Attribute
    def wavenumber(self):
        """Gyroid wavenumber (rad/m)."""
        n_cells = max(1, round(self.solidity * 15))
        L = self.enc_length_x / 1000.0
        return 2.0 * math.pi * n_cells / L if L > 0 else 62.8

    @Attribute
    def pressure_drop(self):
        """Estimated pressure drop (Pa)."""
        L = self.enc_length_x / 1000.0
        D_h = self.hydraulic_diameter
        rho = self.fluid_density
        U = self.bulk_velocity
        return self.friction_factor * (L / D_h) * 0.5 * rho * U**2 if D_h > 0 else 0.0

    # ==================================================================
    # Geometry parts (visible in ParaPy 3D viewport)
    # ==================================================================

    @Part
    def enclosure(self):
        """The heat exchanger enclosure box."""
        return Box(
            width=self.enc_length_x,
            length=self.enc_length_y,
            height=self.enc_length_z,
            color="lightblue",
            transparency=0.6
        )

    # ==================================================================
    # @action — launches the workflow wizard
    # ==================================================================

    @action(label="Open Workflow Wizard")
    def open_workflow(self):
        """Opens the wxFormBuilder wizard as a popup.
        The wizard receives `self` (this ParaPy object) so it can
        read Attributes and write back to Inputs."""
        import wx
        from workflow import WorkflowWizard

        app = wx.GetApp()
        parent = app.GetTopWindow()
        frm = WorkflowWizard(parent, parapy_obj=self)
        frm.Show()
        return "Workflow wizard opened."


# ==================================================================
# Entry point
# ==================================================================

if __name__ == '__main__':
    from parapy.gui import display
    obj = HeatExchanger(label="Heat Exchanger")
    display(obj)
