"""
encapsulation.py
----------------
Parametric CAD of the heat exchanger outer shell and port tubes.

Maps to UML classes: **Encapsulation**, **InletOutletSpecification**

This is the *only* module that creates 3-D geometry visible in the
ParaPy viewport.  Everything else is data / analysis.

Coordinate convention
~~~~~~~~~~~~~~~~~~~~~
  +X → flow direction  (inlet face at x = 0, outlet at x = length)
  +Y → width
  +Z → height
  Origin at the centre of the bottom-left-front corner by default
  (``centered=False`` on the outer box).

API notes (from the ParaPy tutorial exercises):
  * ``translate(pos, 'x', dx, 'y', dy)``   — string-axis form
  * ``rotate90(pos, 'y')``                  — 90° shorthand
  * ``SubtractedSolid(shape_in=…, tool=…)``
  * ``Box(width=…, length=…, height=…, centered=False)``
"""

from math import pi

from parapy.core import Input, Attribute, Part
from parapy.core.validate import Range
from parapy.geom import (GeomBase, Box, Cylinder,
                          SubtractedSolid, FusedSolid,
                          translate, rotate90)


class InletOutletSpec(GeomBase):
    """Single port (inlet or outlet) consisting of a tube + flange.

    The tube axis is aligned with the *local X* after a 90° rotation,
    so it protrudes perpendicular to the encapsulation face.
    """

    #: Internal bore diameter  [m]
    diameter: float = Input(0.010, validator=Range(1e-3, 0.5))

    #: Tube wall thickness  [m]
    tube_wall: float = Input(0.001, validator=Range(1e-4, 0.02))

    #: Stub length beyond the shell face  [m]
    tube_length: float = Input(0.020, validator=Range(1e-3, 0.5))

    #: Flange outer diameter  [m]
    flange_diameter: float = Input(0.020, validator=Range(2e-3, 1.0))

    #: Flange thickness  [m]
    flange_thickness: float = Input(0.003, validator=Range(5e-4, 0.05))

    #: Display colour
    tube_color: str = Input("DarkGreen")

    @Attribute
    def tube_outer_radius(self) -> float:
        """Outer radius of the tube (bore + wall)  [m]."""
        return self.diameter / 2 + self.tube_wall

    @Part
    def tube(self):
        """Cylindrical tube.  Default Cylinder axis = Z; we rotate into X."""
        return Cylinder(
            radius=self.tube_outer_radius,
            height=self.tube_length,
            position=rotate90(self.position, 'y'),
            color=self.tube_color,
            transparency=0.2,
        )

    @Part
    def flange(self):
        """Disc flange at the free end of the tube."""
        return Cylinder(
            radius=self.flange_diameter / 2,
            height=self.flange_thickness,
            position=rotate90(self.position, 'y'),
            color=self.tube_color,
            transparency=0.3,
        )

    @Attribute
    def flow_area(self) -> float:
        """Cross-sectional flow area  [m²]"""
        return pi * (self.diameter / 2) ** 2


class Encapsulation(GeomBase):
    """Hollow rectangular shell with cylindrical inlet / outlet ports.

    Important Parts in the product tree
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    * ``shell`` — hollow box  (outer minus inner void)
    * ``inlet`` — InletOutletSpec at x = 0
    * ``outlet`` — InletOutletSpec at x = length
    """

    # ── external dimensions  [m] ─────────────────────────────────────

    length: float = Input(0.10, validator=Range(1e-3, 10.0))
    width:  float = Input(0.05, validator=Range(1e-3, 10.0))
    height: float = Input(0.05, validator=Range(1e-3, 10.0))

    # ── wall ─────────────────────────────────────────────────────────

    wall_thickness: float = Input(
        0.002, validator=Range(2e-4, 0.05))

    # ── port parameters (passed down to InletOutletSpec) ─────────────

    inlet_diameter:    float = Input(0.010)
    outlet_diameter:   float = Input(0.010)
    tube_wall:         float = Input(0.001)
    tube_length:       float = Input(0.020)
    flange_diameter:   float = Input(0.020)
    flange_thickness:  float = Input(0.003)

    # ── display ──────────────────────────────────────────────────────

    mesh_deflection: float = Input(1e-4)

    # ── geometry parts ───────────────────────────────────────────────

    @Part
    def outer_box(self):
        return Box(
            width=self.width,
            length=self.length,
            height=self.height,
            centered=False,
            position=self.position,
            color="SteelBlue",
            transparency=0.7,
            mesh_deflection=self.mesh_deflection,
        )

    @Part
    def inner_void(self):
        """Cavity subtracted from the outer box to form the shell."""
        return Box(
            width=self.width - 2 * self.wall_thickness,
            length=self.length - 2 * self.wall_thickness,
            height=self.height - 2 * self.wall_thickness,
            centered=False,
            position=translate(self.position,
                               'x', self.wall_thickness,
                               'y', self.wall_thickness,
                               'z', self.wall_thickness),
            color="White",
            hidden=True,
            mesh_deflection=self.mesh_deflection,
        )

    @Part
    def shell(self):
        """Hollow box = outer − inner."""
        return SubtractedSolid(
            shape_in=self.outer_box,
            tool=self.inner_void,
            color="SteelBlue",
            transparency=0.5,
            mesh_deflection=self.mesh_deflection,
        )

    @Part
    def inlet(self):
        """Port at the x = 0 face (flow enters here)."""
        return InletOutletSpec(
            diameter=self.inlet_diameter,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            flange_diameter=self.flange_diameter,
            flange_thickness=self.flange_thickness,
            tube_color="DarkGreen",
            # Translate to centre of the inlet face, then shift back by
            # tube_length so the tube protrudes in −X.
            position=translate(
                self.position,
                'x', -self.tube_length,
                'y', self.width / 2,
                'z', self.height / 2,
            ),
        )

    @Part
    def outlet(self):
        """Port at the x = length face (flow exits here)."""
        return InletOutletSpec(
            diameter=self.outlet_diameter,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            flange_diameter=self.flange_diameter,
            flange_thickness=self.flange_thickness,
            tube_color="FireBrick",
            position=translate(
                self.position,
                'x', self.length,
                'y', self.width / 2,
                'z', self.height / 2,
            ),
        )

    # ── derived attributes ───────────────────────────────────────────

    @Attribute
    def interior_dims(self) -> tuple[float, float, float]:
        """(length, width, height) of the interior cavity  [m]."""
        t = self.wall_thickness
        return (self.length - 2*t, self.width - 2*t, self.height - 2*t)

    @Attribute
    def interior_volume(self) -> float:
        """Volume of the interior cavity  [m³]."""
        l, w, h = self.interior_dims
        return l * w * h

    @Attribute
    def hydraulic_diameter(self) -> float:
        """Dh = 4·A / P  of the rectangular interior cross-section  [m]."""
        _, w, h = self.interior_dims
        return 4 * w * h / (2 * (w + h))

    @Attribute
    def shell_mass(self) -> float:
        """Shell material volume  [m³]  (multiply by density for mass)."""
        return (self.length * self.width * self.height
                - self.interior_volume)
