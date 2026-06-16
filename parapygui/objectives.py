"""
objectives.py
-------------
Optimiser objectives and DfAM manufacturing constraints.

Maps to UML classes: **Objectives**, **ManufacturingConstraintSet**
"""

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range, OneOf


OPTIMISER_MODES = (
    "pressure",
    "heat",
)


class ManufacturingConstraintSet(Base):
    """Design-for-Additive-Manufacturing constraints for LPBF.

    These feed into the manufacturability penalty term in the
    topology optimiser (method from doi:10.1016/j.ijheatmasstransfer.2024.126299).
    """

    #: Maximum unsupported overhang angle from vertical  [deg]
    max_overhang_angle: float = Input(
        45.0, validator=Range(0.0, 90.0))

    #: Machine build volume  (L, W, H)  [m]
    build_volume: tuple = Input((0.25, 0.25, 0.30))

    @Attribute
    def grpc_patch_dict(self) -> dict:
        return {
            "optimization.max_overhang_angle": self.max_overhang_angle,
        }

    def check_fits(self, length, width, height) -> bool:
        """True if the encapsulation fits in the build volume."""
        bv = self.build_volume
        return length <= bv[0] and width <= bv[1] and height <= bv[2]


class Objectives(Base):
    """What the optimiser tries to achieve."""

    #: Optimiser mode — which quantity to minimise
    mode: str = Input(
        "pressure",
        validator=OneOf(OPTIMISER_MODES))

    #: Target Nusselt number (constraint when minimising dissipation)
    target_nusselt: float = Input(
        10.0, validator=Range(1.0, 1e5))

    #: Operating Reynolds number (turbulent flight condition)
    operating_reynolds: float = Input(
        1000.0, validator=Range(1.0, 1e7))

    @Attribute
    def grpc_patch_dict(self) -> dict:
        return {
            "optimization.mode":           self.mode,
            "optimization.target_nusselt": self.target_nusselt,
        }
