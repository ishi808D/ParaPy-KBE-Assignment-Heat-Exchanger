"""
fluid.py
--------
Thermophysical properties of the coolant fluid.

Maps to UML class: **FluidElement**

Defaults are dry air at 20 °C / 1 atm (the MTC electronic-cooling baseline).
"""

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class FluidElement(Base):
    """Coolant fluid properties.  All SI units."""

    #: Dynamic viscosity  [Pa·s]
    dynamic_viscosity: float = Input(
        1.81e-5, validator=Range(1e-7, 1e-1))

    #: Thermal conductivity  [W/(m·K)]
    conductivity: float = Input(
        0.0257, validator=Range(1e-4, 1e3))

    #: Density  [kg/m³]
    density: float = Input(
        1.204, validator=Range(1e-3, 2e4))

    #: Isobaric specific heat capacity  [J/(kg·K)]
    specific_heat: float = Input(
        1005.0, validator=Range(1.0, 1e5))

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def kinematic_viscosity(self) -> float:
        """ν = μ / ρ   [m²/s]"""
        return self.dynamic_viscosity / self.density

    @Attribute
    def prandtl_number(self) -> float:
        """Pr = μ·cp / k   [-]"""
        return (self.dynamic_viscosity * self.specific_heat
                / self.conductivity)

    @Attribute
    def thermal_diffusivity(self) -> float:
        """α = k / (ρ·cp)   [m²/s]"""
        return self.conductivity / (self.density * self.specific_heat)
