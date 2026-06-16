"""
solidity.py
-----------
Semi-empirical sizing rules from Femmer et al. (2023):
    "Correlations for TPMS heat exchangers"
    Energy Conversion and Management, 116955
    https://doi.org/10.1016/j.enconman.2023.116955

Maps to UML class: **SemiEmpirical** (called ``correlateNu``,
``evaluateStability``, ``extrapolateAll`` in the diagram).

This class is purely computational — no geometry, no gRPC calls.
"""

from math import pi

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class SemiEmpirical(Base):
    """Gyroid-specific Nusselt / friction correlations.

    The key output is ``required_solidity``: the minimum solid volume
    fraction φ needed to hit ``target_nusselt`` at the simulation
    Reynolds number.  This value is passed to the MTO backend as
    the initial wall thickness estimate.

    Laminar-to-turbulent extrapolation uses a simple power-law ratio
    of Reynolds numbers, preserving the Femmer exponent β.
    """

    # ── operating point (set by HeatExchanger) ───────────────────────

    hydraulic_diameter:         float = Input(validator=Range(1e-4, 1.0))
    inflow_velocity:            float = Input(validator=Range(1e-4, 1e3))
    kinematic_viscosity:        float = Input(validator=Range(1e-8, 1e-2))
    fluid_conductivity:         float = Input(validator=Range(1e-4, 1e3))
    prandtl_number:             float = Input(validator=Range(0.001, 1e4))

    # ── design target ────────────────────────────────────────────────

    target_nusselt:    float = Input(10.0, validator=Range(1.0, 1e5))
    operating_re:      float = Input(1000.0, validator=Range(1.0, 1e7))
    simulation_re:     float = Input(100.0, validator=Range(0.1, 1e6))

    # ── Femmer correlation coefficients (gyroid defaults) ────────────

    C1:    float = Input(0.956)    # Eq. 7
    alpha: float = Input(0.404)    # Eq. 7  (solidity exponent)
    C2:    float = Input(0.664)    # Eq. 9  (Re/Pr correlation)
    beta:  float = Input(0.5)      # Eq. 9  (Reynolds exponent)

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def reynolds_number(self) -> float:
        """Re at the current inlet conditions."""
        return (self.inflow_velocity * self.hydraulic_diameter
                / self.kinematic_viscosity)

    @Attribute
    def nu_laminar(self) -> float:
        """Predicted Nu at *simulation* Re (laminar).
        Nu = C2 · Re_sim^β · Pr^(1/3)
        """
        return (self.C2
                * self.simulation_re ** self.beta
                * self.prandtl_number ** (1.0 / 3.0))

    @Attribute
    def lam_turb_factor(self) -> float:
        """Scale factor:  (Re_operating / Re_simulation)^β."""
        return (self.operating_re / max(self.simulation_re, 1e-12)) ** self.beta

    @Attribute
    def nu_turbulent(self) -> float:
        """Extrapolated Nu at operating (turbulent) Re."""
        return self.nu_laminar * self.lam_turb_factor

    @Attribute
    def required_solidity(self) -> float:
        """Minimum solid volume fraction φ.

        Inverts  Nu = C1 · φ^α · C2 · Re^β · Pr^(1/3)
        →  φ = [ Nu_target / (C1 · C2 · Re^β · Pr^(1/3)) ] ^ (1/α)

        Clamped to [0.05, 0.95].
        """
        denom = self.C1 * self.nu_laminar
        if denom <= 0:
            return 0.5
        raw = (self.target_nusselt / denom) ** (1.0 / self.alpha)
        return max(0.05, min(0.95, raw))

    @Attribute
    def wall_thickness_estimate(self) -> float:
        """Back-calculated wall thickness  [m].
        Approximate:  t ≈ φ · Dh / π
        """
        return self.required_solidity * self.hydraulic_diameter / pi

    @Attribute
    def heat_transfer_coeff(self) -> float:
        """h = Nu_turb · k_fluid / Dh   [W/(m²·K)]."""
        return (self.nu_turbulent * self.fluid_conductivity
                / self.hydraulic_diameter)

    @Attribute
    def summary(self) -> dict:
        """Flat dict for PDF report and design_summary."""
        return {
            "Re":                 round(self.operating_re, 1),
            "Nu":                   round(self.nu_laminar, 3),
            "wall_thickness_est_mm":        round(self.wall_thickness_estimate * 1e3, 4),
            "h_W_m2K":                      round(self.heat_transfer_coeff, 2),
        }
