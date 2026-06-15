"""
encapsulation.py
----------------
Parametric CAD of the heat exchanger outer shell and port geometry.

Ports are rectangular (matching the server's rectangular window patches)
and are properly parameterized relative to the encapsulation geometry:
  - Flush with the outer shell face
  - Bore penetrates through the wall into the interior cavity
  - Tube protrudes outward by tube_length
  - Port offset from face centre is configurable
"""

from parapy.core import Input, Attribute, Part
from parapy.core.validate import Range
from parapy.geom import (GeomBase, Box, SubtractedSolid, translate)


class InletOutletSpec(GeomBase):
    """Single rectangular port (inlet or outlet).

    Position should be at the OUTER shell face, centred on the port.
    The tube protrudes outward (+X for outlet, -X for inlet).
    """

    bore_width:   float = Input(0.010, validator=Range(1e-3, 0.5))
    bore_height:  float = Input(0.015, validator=Range(1e-3, 0.5))
    tube_wall:    float = Input(0.001, validator=Range(1e-4, 0.02))
    tube_length:  float = Input(0.020, validator=Range(1e-3, 0.5))
    shell_wall:   float = Input(0.003, validator=Range(1e-4, 0.05))
    tube_color:   str   = Input("DarkBlue")
    is_inlet:     bool  = Input(True)

    @Attribute
    def tube_outer_w(self):
        return self.bore_width + 2 * self.tube_wall

    @Attribute
    def tube_outer_h(self):
        return self.bore_height + 2 * self.tube_wall

    @Attribute
    def direction(self):
        """Outward direction multiplier: -1 for inlet (protrudes in -X), +1 for outlet."""
        return -1.0 if self.is_inlet else 1.0

    @Part
    def tube(self):
        """Rectangular tube protruding outward from the shell face."""
        return Box(
            width=self.tube_outer_w,
            length=self.tube_length,
            height=self.tube_outer_h,
            centered=False,
            position=translate(self.position,
                               'x', 0 if self.direction > 0 else -self.tube_length,
                               'y', -self.tube_outer_w / 2,
                               'z', -self.tube_outer_h / 2),
            color=self.tube_color,
            transparency=0.2,
        )

    @Part
    def bore(self):
        """Rectangular bore cutting through the wall + tube.
        Used as a boolean tool to create the port hole in the shell."""
        return Box(
            width=self.bore_width,
            length=self.tube_length + self.shell_wall + 0.001,
            height=self.bore_height,
            centered=False,
            position=translate(self.position,
                               'x', -self.shell_wall - 0.0005,
                               'y', -self.bore_width / 2,
                               'z', -self.bore_height / 2),
            color="White",
            hidden=True,
        )

    @Attribute
    def flow_area(self):
        return self.bore_width * self.bore_height


class Encapsulation(GeomBase):
    """Hollow rectangular shell with inlet/outlet ports.

    Ports are parameterized relative to the shell:
    - Position is derived from shell dimensions + offsets
    - Bore cuts through the shell wall
    - Ports never float — they're always flush with the face
    """

    length:         float = Input(0.250, validator=Range(1e-3, 10.0))
    width:          float = Input(0.250, validator=Range(1e-3, 10.0))
    height:         float = Input(0.300, validator=Range(1e-3, 10.0))
    wall_thickness: float = Input(0.003, validator=Range(2e-4, 0.05))

    # port bore matches server window_size_mm / 1000
    inlet_bore_width:   float = Input(0.010)
    inlet_bore_height:  float = Input(0.015)
    outlet_bore_width:  float = Input(0.010)
    outlet_bore_height: float = Input(0.015)

    # port centre offset from face centre [m]
    inlet_offset_y:  float = Input(0.0)
    inlet_offset_z:  float = Input(0.0)
    outlet_offset_y: float = Input(0.0)
    outlet_offset_z: float = Input(0.0)

    tube_wall:       float = Input(0.001)
    tube_length:     float = Input(0.020)
    mesh_deflection: float = Input(1e-4)

    # ── geometry ─────────────────────────────────────────────────────

    @Part
    def outer_box(self):
        return Box(width=self.width, length=self.length, height=self.height,
                   centered=False, position=self.position,
                   color="SteelBlue", transparency=0.7,
                   mesh_deflection=self.mesh_deflection)

    @Part
    def inner_void(self):
        """Cavity subtracted to form the shell."""
        return Box(
            width=self.width - 2 * self.wall_thickness,
            length=self.length - 2 * self.wall_thickness,
            height=self.height - 2 * self.wall_thickness,
            centered=False,
            position=translate(self.position,
                               'x', self.wall_thickness,
                               'y', self.wall_thickness,
                               'z', self.wall_thickness),
            color="White", hidden=True,
            mesh_deflection=self.mesh_deflection)

    @Part
    def shell_basic(self):
        """Hollow box before port holes."""
        return SubtractedSolid(shape_in=self.outer_box, tool=self.inner_void,
                               color="SteelBlue", transparency=0.5,
                               hidden=True, mesh_deflection=self.mesh_deflection)

    @Part
    def shell_with_inlet(self):
        """Shell with inlet bore cut."""
        return SubtractedSolid(shape_in=self.shell_basic, tool=self.inlet.bore,
                               color="SteelBlue", transparency=0.5,
                               hidden=True, mesh_deflection=self.mesh_deflection)

    @Part
    def shell(self):
        """Final shell with both port holes."""
        return SubtractedSolid(shape_in=self.shell_with_inlet, tool=self.outlet.bore,
                               color="SteelBlue", transparency=0.5,
                               mesh_deflection=self.mesh_deflection)

    @Part
    def inlet(self):
        """Port at x=0 face. Parameterized from shell dimensions."""
        return InletOutletSpec(
            bore_width=self.inlet_bore_width,
            bore_height=self.inlet_bore_height,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            shell_wall=self.wall_thickness,
            tube_color="DarkGreen",
            is_inlet=True,
            position=translate(self.position,
                               'x', 0,
                               'y', self.width / 2 + self.inlet_offset_y,
                               'z', self.height / 2 + self.inlet_offset_z))

    @Part
    def outlet(self):
        """Port at x=length face. Parameterized from shell dimensions."""
        return InletOutletSpec(
            bore_width=self.outlet_bore_width,
            bore_height=self.outlet_bore_height,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            shell_wall=self.wall_thickness,
            tube_color="FireBrick",
            is_inlet=False,
            position=translate(self.position,
                               'x', self.length,
                               'y', self.width / 2 + self.outlet_offset_y,
                               'z', self.height / 2 + self.outlet_offset_z))

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def interior_dims(self):
        t = self.wall_thickness
        return (self.length - 2*t, self.width - 2*t, self.height - 2*t)

    @Attribute
    def interior_volume(self):
        l, w, h = self.interior_dims
        return l * w * h

    @Attribute
    def hydraulic_diameter(self):
        _, w, h = self.interior_dims
        return 4 * w * h / (2 * (w + h))

    @Attribute
    def shell_volume(self):
        return self.length * self.width * self.height - self.interior_volume
