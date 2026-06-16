"""
environment.py
--------------
Boundary conditions and flow parameters for the heat exchanger system.

Maps to UML class: **HeatExchangerEnvironment**
"""

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class HeatExchangerEnvironment(Base):
    """Operating-point boundary conditions.

    These values, together with the geometry and fluid properties,
    fully define a single CFD simulation case.
    """

    #: Mean inlet velocity  [m/s]
    inflow_velocity: float = Input(
        1.0, validator=Range(1e-4, 500.0))

    #: Inlet fluid temperature  [K]
    inflow_temperature: float = Input(
        350.0, validator=Range(200.0, 2000.0))

    #: Static pressure at the outlet  [Pa]
    outlet_pressure: float = Input(
        101325.0, validator=Range(0.0, 1e8))

    #: Ambient / exterior wall temperature  [K]
    exterior_temperature: float = Input(
        293.15, validator=Range(1.0, 2000.0))

    #: Wall heat conduction rate  [W/(m²·K)]
    wall_heat_conduction: float = Input(
        10.0, validator=Range(0.0, 1e6))


    #: Mechanical dissipation upper bound (constraint)  [W]
    mech_dissipation_upper: float = Input(10.0)

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def delta_T(self) -> float:
        """Temperature difference driving the heat exchange  [K]."""
        return self.inflow_temperature - self.exterior_temperature

    @Attribute
    def grpc_patch_dict(self) -> dict:
        """Key-value pairs for ``client.py patch-config``."""
        return {
            "run.inflow_velocity":      self.inflow_velocity,
            "run.inflow_temperature":   self.inflow_temperature,
            "run.outlet_pressure":      self.outlet_pressure,
            "run.exterior_temperature": self.exterior_temperature,
            "run.wall_heat_conduction": self.wall_heat_conduction,
        }
