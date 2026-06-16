"""
encapsulation.py  –  Parametric heat-exchanger shell + ports

Coordinate convention (matches ParaPy Box: width=X, length=Y, height=Z):
  +X → flow direction  (Box.width = self.length)
  +Y → transverse      (Box.length = self.width)
  +Z → vertical        (Box.height = self.height)
  Origin at minimum corner (centered=False).

Ports are flush with the shell face and bore through the wall.
"""

from math import pi

from parapy.core import Input, Attribute, Part
from parapy.core.validate import Range
from parapy.geom import GeomBase, Box, SubtractedSolid, translate

from gyroid import GyroidMesh


class InletOutletSpec(GeomBase):
    """Rectangular port: tube protruding from the shell + bore through wall."""

    bore_width:   float = Input(0.010, validator=Range(1e-3, 0.5))
    bore_height:  float = Input(0.015, validator=Range(1e-3, 0.5))
    tube_wall:    float = Input(0.001, validator=Range(1e-4, 0.02))
    tube_length:  float = Input(0.020, validator=Range(1e-3, 0.5))
    shell_wall:   float = Input(0.003, validator=Range(1e-4, 0.05))
    tube_color:   str   = Input("DarkGreen")
    is_inlet:     bool  = Input(True)

    @Attribute
    def tube_outer_w(self):
        return self.bore_width + 2 * self.tube_wall

    @Attribute
    def tube_outer_h(self):
        return self.bore_height + 2 * self.tube_wall

    @Attribute
    def tube_x_start(self):
        return -self.tube_length if self.is_inlet else 0.0

    @Attribute
    def bore_total_x(self):
        return self.tube_length + self.shell_wall + 0.002

    @Attribute
    def bore_x_start(self):
        return -self.tube_length - 0.001 if self.is_inlet else -self.shell_wall - 0.001

    @Part
    def tube(self):
        """Rectangular tube protruding from the shell face along X."""
        return Box(
            width=self.tube_length,
            length=self.tube_outer_w,
            height=self.tube_outer_h,
            centered=False,
            position=translate(self.position,
                               'x', self.tube_x_start,
                               'y', -self.tube_outer_w / 2,
                               'z', -self.tube_outer_h / 2),
            color=self.tube_color,
            transparency=0.2,
        )

    @Part
    def bore(self):
        """Rectangular bore cutting through the wall."""
        return Box(
            width=self.bore_total_x,
            length=self.bore_width,
            height=self.bore_height,
            centered=False,
            position=translate(self.position,
                               'x', self.bore_x_start,
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

    Box mapping: width=length(X), length=width(Y), height=height(Z).
    Ports parameterized relative to the shell faces.
    """

    # external dimensions [m]
    length:         float = Input(0.250, validator=Range(1e-3, 10.0))
    width:          float = Input(0.250, validator=Range(1e-3, 10.0))
    height:         float = Input(0.300, validator=Range(1e-3, 10.0))
    wall_thickness: float = Input(0.003, validator=Range(2e-4, 0.05))

    # port bore dimensions [m] (matches server window_size_mm / 1000)
    inlet_bore_width:   float = Input(0.010)
    inlet_bore_height:  float = Input(0.015)
    outlet_bore_width:  float = Input(0.010)
    outlet_bore_height: float = Input(0.015)

    # port offset from face centre [m]
    inlet_offset_y:  float = Input(0.0)
    inlet_offset_z:  float = Input(0.0)
    outlet_offset_y: float = Input(0.0)
    outlet_offset_z: float = Input(0.0)

    tube_wall:       float = Input(0.001)
    tube_length:     float = Input(0.020)
    mesh_deflection: float = Input(1e-4)

    #: base wavenumber for the gyroid [rad/m]; 2π/k = unit-cell size
    k_base:    float = Input(2 * pi / 0.010)
    iso_level: float = Input(0.5)

    # ── geometry ─────────────────────────────────────────────────────

    @Part
    def outer_box(self):
        """Outer shell. width=length(X), length=width(Y), height(Z)."""
        return Box(
            width=self.length,       # X = flow direction
            length=self.width,       # Y = transverse
            height=self.height,      # Z = vertical
            centered=False,
            position=self.position,
            color="SteelBlue", transparency=0.7,
            mesh_deflection=self.mesh_deflection)

    @Part
    def inner_void(self):
        """Cavity subtracted to form the shell."""
        return Box(
            width=self.length - 2 * self.wall_thickness,
            length=self.width - 2 * self.wall_thickness,
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
        return SubtractedSolid(
            shape_in=self.outer_box, tool=self.inner_void,
            color="SteelBlue", transparency=0.5, hidden=True,
            mesh_deflection=self.mesh_deflection)

    @Part
    def shell_with_inlet(self):
        """Shell with inlet bore cut."""
        return SubtractedSolid(
            shape_in=self.shell_basic, tool=self.inlet.bore,
            color="SteelBlue", transparency=0.5, hidden=True,
            mesh_deflection=self.mesh_deflection)

    @Part
    def shell(self):
        """Final shell with both port holes."""
        return SubtractedSolid(
            shape_in=self.shell_with_inlet, tool=self.outlet.bore,
            color="SteelBlue", transparency=0.5,
            mesh_deflection=self.mesh_deflection)

    @Part
    def inlet(self):
        """Port at x=0 face (flow entrance). Centred on the YZ face."""
        return InletOutletSpec(
            bore_width=self.inlet_bore_width,
            bore_height=self.inlet_bore_height,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            shell_wall=self.wall_thickness,
            tube_color="DarkGreen",
            is_inlet=True,
            position=translate(self.position,
                               'x', 0,                                   # x=0 face
                               'y', self.width / 2 + self.inlet_offset_y,
                               'z', self.height / 2 + self.inlet_offset_z))

    @Part
    def outlet(self):
        """Port at x=length face (flow exit). Centred on the YZ face."""
        return InletOutletSpec(
            bore_width=self.outlet_bore_width,
            bore_height=self.outlet_bore_height,
            tube_wall=self.tube_wall,
            tube_length=self.tube_length,
            shell_wall=self.wall_thickness,
            tube_color="FireBrick",
            is_inlet=False,
            position=translate(self.position,
                               'x', self.length,                           # x=length face
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
    def enclosed_volume(self):
        return self.length * self.width * self.height
    
    @Attribute
    def enclosed_gyroid_surface_area(self):
        """Approximate surface area of the gyroid if it filled the entire enclosure."""
        mesh = GyroidMesh(
            length=self.length,
            width=self.width,
            height=self.height,
            kx=[self.k_base],
            ky=[self.k_base],
            kz=[self.k_base],
            iso_level=self.iso_level,
        )
        return mesh.surface_area


    @Attribute
    def hydraulic_diameter(self):
        _, w, h = self.interior_dims
        return 4*self.enclosed_volume / self.enclosed_gyroid_surface_area

    @Attribute
    def shell_volume(self):
        return self.enclosed_volume - self.interior_volume
    
    @Attribute
    def inlet_window_size(self):
        return self.inlet_bore_width * self.inlet_bore_height
