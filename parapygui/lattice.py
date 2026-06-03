"""
lattice.py
----------
TPMS lattice description passed to the MTO topology optimiser.

Maps to UML classes: **LatticeElement**, **TPMSFrequencyField**,
**LatticeFormulation**

ParaPy / OpenCascade cannot represent the implicit TPMS surface directly
(confirmed by ParaPy B.V.).  These classes hold the *parameters* that
the MTO backend needs; actual geometry lives in OpenFOAM.
"""

from math import pi

from parapy.core import Base, Input, Attribute, Part
from parapy.core.validate import Range


class LatticeElement(Base):
    """Solid-phase material of the lattice walls."""

    #: Solid density  [kg/m³]   (default: Ti-6Al-4V for LPBF)
    density: float = Input(
        4430.0, validator=Range(500.0, 2e4))

    #: Volumetric heat capacity  [J/(m³·K)]
    volumetric_heat_capacity: float = Input(2.35e6)


class TPMSFrequencyField(Base):
    """Radial-basis-interpolated wavenumber field over the bounding box.

    Three scalar fields kx(x,y,z), ky(x,y,z), kz(x,y,z) specify the
    local unit-cell frequency.  They are sampled at ``n_ctrl`` control
    points whose locations sit inside the interior volume.

    Example (gyroid):  sin(kx·x)cos(ky·y) + sin(ky·y)cos(kz·z)
                       + sin(kz·z)cos(kx·x) = 0
    """

    #: (x, y, z) tuples of control-point positions  [m]
    ctrl_locations: list = Input()

    #: kx at each control point  [rad/m]
    kx: list = Input()

    #: ky at each control point  [rad/m]
    ky: list = Input()

    #: kz at each control point  [rad/m]
    kz: list = Input()

    @Attribute
    def n_ctrl(self) -> int:
        return len(self.ctrl_locations)

    @Attribute
    def is_consistent(self) -> bool:
        n = self.n_ctrl
        return len(self.kx) == n and len(self.ky) == n and len(self.kz) == n

    @Attribute
    def mean_wavenumber(self) -> float:
        """Arithmetic mean across all control points and axes  [rad/m]."""
        if self.n_ctrl == 0:
            return 0.0
        return (sum(self.kx) + sum(self.ky) + sum(self.kz)) / (3 * self.n_ctrl)

    @Attribute
    def mean_unit_cell_size(self) -> float:
        """2π / mean_wavenumber  [m].  Returns inf when k = 0."""
        k = self.mean_wavenumber
        return (2 * pi / k) if k > 0 else float("inf")


class LatticeFormulation(Base):
    """Collects material + frequency field + DfAM constraints.

    This is what gets serialised and sent to the gRPC server before each run.
    """

    #: TPMS type identifier  (default: gyroid)
    tpms_type: str = Input("gyroid")

    #: Wall thickness extruded from the zero-level surface  [m]
    wall_thickness: float = Input(
        3e-4, validator=Range(5e-5, 5e-3))

    @Part
    def material(self):
        return LatticeElement()

    @Part
    def frequency_field(self):
        return TPMSFrequencyField(
            ctrl_locations=self._default_ctrl,
            kx=self._default_k,
            ky=self._default_k,
            kz=self._default_k,
        )

    # ── private helpers (overridden by HeatExchanger) ────────────────

    _default_ctrl: list = Input([(0, 0, 0)])
    _default_k: list = Input([62.8])

    @Attribute
    def solidity_estimate(self) -> float:
        """Rough solidity from wall_thickness / unit_cell_size.
        Proper value is computed by SemiEmpirical."""
        uc = self.frequency_field.mean_unit_cell_size
        if uc == float("inf"):
            return 0.0
        return min(0.95, self.wall_thickness / (uc / pi))

    @Attribute
    def grpc_patch_dict(self) -> dict:
        """Key-value pairs for ``client.py patch-config``."""
        ff = self.frequency_field
        return {
            "lattice.tpms_type":       self.tpms_type,
            "lattice.wall_thickness":  self.wall_thickness,
            "lattice.kx_values":       str(ff.kx),
            "lattice.ky_values":       str(ff.ky),
            "lattice.kz_values":       str(ff.kz),
            "lattice.ctrl_locations":  str(ff.ctrl_locations),
        }
