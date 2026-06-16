"""
gyroid.py
---------
Gyroid mesh generation for live design-space exploration.

Maps to UML classes: **VoxelGeometryRepresentation**, **GeometryRepresentation**

ParaPy / OpenCascade cannot evaluate implicit surfaces, so this module
does the implicit→mesh conversion in NumPy:

    1. Evaluate the gyroid field F(x,y,z) on a voxel grid, using the
       RBF-interpolated wavenumber fields kx, ky, kz.
    2. Extract the sheet-gyroid wall (region |F| < c) as two iso-surfaces
       via marching cubes.
    3. Expose vertices / faces / solidity / mass as attributes.
    4. Write STL (binary) for the ParaPy viewer and for export.

The resolution input controls speed vs. fidelity:
    * preview   ~  (40, 20, 20)   → fast, for live slider feedback
    * export    ~ (160, 80, 80)   → slow, for the final STL deliverable
"""

from __future__ import annotations

import struct
from math import pi
from pathlib import Path

import numpy as np

from parapy.core import Base, Input, Attribute


def _gyroid(X, Y, Z, kx, ky, kz):
    return (np.sin(kx * X) * np.cos(ky * Y) +
            np.sin(ky * Y) * np.cos(kz * Z) +
            np.sin(kz * Z) * np.cos(kx * X))


class GyroidMesh(Base):
    """Voxelised TPMS lattice mesh for a single design point.

    The wavenumber at each voxel is interpolated from the control-point
    field using inverse-distance weighting (a lightweight stand-in for the
    full RBF the optimiser uses — adequate for live preview).
    """

    # ── bounding box  [m] ────────────────────────────────────────────

    length: float = Input(0.10)
    width:  float = Input(0.05)
    height: float = Input(0.05)

    # ── wavenumber field ─────────────────────────────────────────────

    #: control-point locations  [(x,y,z), …]  in metres
    ctrl_locations: list = Input([(0.05, 0.025, 0.025)])
    kx: list = Input([628.0])
    ky: list = Input([628.0])
    kz: list = Input([628.0])

    #: iso-level controlling wall thickness / solidity  (|F| < iso = solid)
    iso_level: float = Input(0.3)

    # ── resolution ───────────────────────────────────────────────────

    #: voxels along the longest edge; others scale proportionally
    resolution: int = Input(60)

    #: solid material density  [kg/m³]  (Ti-6Al-4V default)
    material_density: float = Input(4430.0)

    # ── grid ─────────────────────────────────────────────────────────

    @Attribute
    def grid_shape(self) -> tuple[int, int, int]:
        """(nx, ny, nz) voxel counts, scaled from resolution."""
        longest = max(self.length, self.width, self.height)
        nx = max(8, round(self.resolution * self.length / longest))
        ny = max(8, round(self.resolution * self.width / longest))
        nz = max(8, round(self.resolution * self.height / longest))
        return (nx, ny, nz)

    @Attribute
    def spacing(self) -> tuple[float, float, float]:
        nx, ny, nz = self.grid_shape
        return (self.length / (nx - 1),
                self.width / (ny - 1),
                self.height / (nz - 1))

    @Attribute
    def wavenumber_grids(self):
        """Interpolated (KX, KY, KZ) arrays over the voxel grid.

        Uses inverse-distance weighting from the control points.
        Returns three numpy arrays of shape grid_shape.
        """
        nx, ny, nz = self.grid_shape
        xs = np.linspace(0, self.length, nx)
        ys = np.linspace(0, self.width, ny)
        zs = np.linspace(0, self.height, nz)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")

        pts = np.asarray(self.ctrl_locations, dtype=float)  # (M,3)
        kx = np.asarray(self.kx, dtype=float)
        ky = np.asarray(self.ky, dtype=float)
        kz = np.asarray(self.kz, dtype=float)

        if len(pts) == 1:
            # Uniform field — fast path
            return (np.full(X.shape, kx[0]),
                    np.full(X.shape, ky[0]),
                    np.full(X.shape, kz[0]))

        # Inverse-distance weighting
        KX = np.zeros(X.shape)
        KY = np.zeros(X.shape)
        KZ = np.zeros(X.shape)
        wsum = np.zeros(X.shape)
        eps = 1e-9
        for i, (px, py, pz) in enumerate(pts):
            d2 = (X - px)**2 + (Y - py)**2 + (Z - pz)**2 + eps
            w = 1.0 / d2
            KX += w * kx[i]
            KY += w * ky[i]
            KZ += w * kz[i]
            wsum += w
        return (KX / wsum, KY / wsum, KZ / wsum)

    @Attribute
    def field(self):
        """The TPMS implicit field F on the voxel grid (numpy array)."""
        nx, ny, nz = self.grid_shape
        xs = np.linspace(0, self.length, nx)
        ys = np.linspace(0, self.width, ny)
        zs = np.linspace(0, self.height, nz)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
        KX, KY, KZ = self.wavenumber_grids
        return _gyroid(X, Y, Z, KX, KY, KZ)

    # ── derived mesh ─────────────────────────────────────────────────

    @Attribute
    def mesh(self):
        """(vertices, faces, normals) of the sheet-gyroid wall.

        Combines the +iso and −iso marching-cubes surfaces into one mesh.
        Clamps the iso-level into the field's actual range so marching cubes
        never raises on an out-of-range level.
        """
        from skimage import measure
        F = self.field
        sp = self.spacing
        fmin, fmax = float(F.min()), float(F.max())
        # leave a small margin so a surface always exists
        margin = 0.02 * (fmax - fmin)
        level = max(fmin + margin, min(fmax - margin, self.iso_level))
        v1, f1, n1, _ = measure.marching_cubes(F, level=level, spacing=sp)
        v2, f2, n2, _ = measure.marching_cubes(F, level=-level, spacing=sp)
        verts = np.vstack([v1, v2])
        faces = np.vstack([f1, f2 + len(v1)])
        normals = np.vstack([n1, n2])
        return verts, faces, normals

    @Attribute
    def face_normals(self):
        """Per-face unit normals  (N,3) numpy array."""
        verts, faces, _ = self.mesh
        tris = verts[faces]
        n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        return np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)

    @Attribute
    def face_areas(self):
        """Per-face triangle areas  (N,) numpy array  [m²]."""
        verts, faces, _ = self.mesh
        tris = verts[faces]
        cross = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
        return 0.5 * np.linalg.norm(cross, axis=1)

    @Attribute
    def solidity(self) -> float:
        """Solid volume fraction = fraction of voxels with |F| < iso_level."""
        F = self.field
        return float((np.abs(F) < self.iso_level).mean())

    @Attribute
    def solid_volume(self) -> float:
        """Solid material volume  [m³]."""
        return self.solidity * self.length * self.width * self.height

    @Attribute
    def mass(self) -> float:
        """Lattice mass  [kg] = solid_volume × material_density."""
        return self.solid_volume * self.material_density

    @Attribute
    def surface_area(self) -> float:
        """Total wall surface area  [m²]  (sum of triangle areas)."""
        verts, faces, _ = self.mesh
        v0 = verts[faces[:, 0]]
        v1 = verts[faces[:, 1]]
        v2 = verts[faces[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        return float(0.5 * np.linalg.norm(cross, axis=1).sum())

    @Attribute
    def n_triangles(self) -> int:
        _, faces, _ = self.mesh
        return len(faces)

    # ── STL output ───────────────────────────────────────────────────

    def write_stl(self, path: str) -> str:
        """Write the lattice mesh to a binary STL file.  Returns the path."""
        verts, faces, _ = self.mesh
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tris = verts[faces]                       # (N,3,3)
        n = np.cross(tris[:, 1] - tris[:, 0],
                     tris[:, 2] - tris[:, 0])
        ln = np.linalg.norm(n, axis=1, keepdims=True)
        n = np.divide(n, ln, out=np.zeros_like(n), where=ln > 0)

        with open(path, "wb") as fh:
            fh.write(b"\0" * 80)                  # header
            fh.write(struct.pack("<I", len(faces)))
            for i in range(len(faces)):
                fh.write(struct.pack("<3f", *n[i]))
                for v in tris[i]:
                    fh.write(struct.pack("<3f", *v))
                fh.write(struct.pack("<H", 0))    # attribute byte count
        return path

    # ── ParaPy viewport display ──────────────────────────────────────

    def write_preview_stl(self, path: str = "outputs/lattice_preview.stl") -> str:
        """Write a coarse STL suitable for quick ParaPy / external viewing.

        ParaPy's OCC kernel struggles to render >50k triangles smoothly,
        so for the live preview use a modest ``resolution`` (≤ 60).
        """
        return self.write_stl(path)
