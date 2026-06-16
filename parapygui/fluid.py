"""
fluid.py
--------
Thermophysical properties of the coolant fluid.

Maps to UML class: **FluidElement**

Defaults match liquid water at ~20 °C (the primary coolant in the heat
exchanger application).  All values are driven from HeatExchanger inputs so
that the GUI and the server config stay consistent; the defaults here are
only used when this class is instantiated stand-alone (e.g. in unit tests).
"""

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class FluidElement(Base):
    """Coolant fluid properties.  All SI units."""

    #: Kinematic viscosity  [m²/s]
    kinematic_viscosity: float = Input(
        1e-6, validator=Range(1e-8, 1e-2))

    #: Thermal conductivity  [W/(m·K)]
    conductivity: float = Input(
        0.61, validator=Range(1e-4, 1e3))

    #: Density  [kg/m³]
    density: float = Input(
        1000.0, validator=Range(1e-3, 2e4))

    #: Isobaric specific heat capacity  [J/(kg·K)]
    specific_heat: float = Input(
        4180.0, validator=Range(1.0, 1e5))

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def dynamic_viscosity(self) -> float:
        """μ = ν · ρ   [Pa·s]"""
        return self.kinematic_viscosity * self.density

    @Attribute
    def prandtl_number(self) -> float:
        """Pr = μ·cp / k   [-]"""
        return (self.dynamic_viscosity * self.specific_heat
                / self.conductivity)

    @Attribute
    def thermal_diffusivity(self) -> float:
        """α = k / (ρ·cp)   [m²/s]"""
        return self.conductivity / (self.density * self.specific_heat)
