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


def _gyroid(X, Y, Z, k):
    return (np.sin(k * X) * np.cos(k * Y) +
            np.sin(k * Y) * np.cos(k * Z) +
            np.sin(k * Z) * np.cos(k * X))


class GyroidMesh(Base):
    """Voxelised TPMS lattice mesh for a single design point.

    The wavenumber at each voxel is interpolated from the control-point
    field using inverse-distance weighting (a lightweight stand-in for the
    full RBF the optimiser uses — adequate for live preview).
    """

    # ── bounding box  [m] ────────────────────────────────────────────

    length: float = Input(0.25)
    width:  float = Input(0.25)
    height: float = Input(0.30)

    # ── spatially-varying wavenumber field (RBF control points) ──────

    ctrl_locations: list = Input([])  # list of (x,y,z) tuples [m]
    kx: list = Input([])              # wavenumber in x at each ctrl point [rad/m]
    ky: list = Input([])              # wavenumber in y at each ctrl point [rad/m]
    kz: list = Input([])              # wavenumber in z at each ctrl point [rad/m]

    #: iso-level controlling wall thickness / solidity  (|F| < iso = solid)
    iso_level: float = Input(0.5)

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
    def _k_mean(self) -> float:
        """Mean wavenumber [rad/m] from the ctrl-point field; falls back to a
        10 mm unit cell when no field has been synced yet."""
        vals = list(self.kx) + list(self.ky) + list(self.kz)
        return float(np.mean(vals)) if vals else 2 * np.pi / 0.010

    @Attribute
    def field(self):
        """The TPMS implicit field F on the voxel grid (numpy array).

        Uses IDW-interpolated wavenumber when ctrl_locations are provided,
        otherwise a uniform k_mean across the whole grid.
        """
        nx, ny, nz = self.grid_shape
        xs = np.linspace(0, self.length, nx)
        ys = np.linspace(0, self.width, ny)
        zs = np.linspace(0, self.height, nz)
        X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")

        if self.ctrl_locations and self.kx:
            pts = np.array(self.ctrl_locations, dtype=float)   # (N,3)
            kx_arr = np.array(self.kx, dtype=float)
            ky_arr = np.array(self.ky, dtype=float) if self.ky else kx_arr
            kz_arr = np.array(self.kz, dtype=float) if self.kz else kx_arr
            xf, yf, zf = X.ravel(), Y.ravel(), Z.ravel()
            coords = np.stack([xf, yf, zf], axis=1)           # (M,3)
            diff = coords[:, None, :] - pts[None, :, :]        # (M,N,3)
            dist2 = (diff ** 2).sum(axis=2) + 1e-12            # (M,N)
            w = 1.0 / dist2                                     # IDW weights
            w /= w.sum(axis=1, keepdims=True)
            k_x = (w * kx_arr).sum(axis=1).reshape(X.shape)
            k_y = (w * ky_arr).sum(axis=1).reshape(Y.shape)
            k_z = (w * kz_arr).sum(axis=1).reshape(Z.shape)
            return (np.sin(k_x * X) * np.cos(k_y * Y) +
                    np.sin(k_y * Y) * np.cos(k_z * Z) +
                    np.sin(k_z * Z) * np.cos(k_x * X))

        return _gyroid(X, Y, Z, self._k_mean)

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
