"""
geometry_export.py
------------------
Geometry file export: STL-to-STEP reconstruction and assembly STEP writer.

Maps to UML classes: **GeometryExportService**, **STLConverter**,
**CGALMeshCleaner**, **ParaPyNURBSReconstructor**

Pipeline
~~~~~~~~
1. MTO produces a voxelated gamma field → a Python script on the server
   converts it to an STL file.
2. ``SimulationConnector.download_stl()`` pulls it locally.
3. This module reads the STL, slices it into cross-sectional contours,
   fits BSplineCurves through them, and lofts a surface.
4. The lofted surface is combined with the Encapsulation shell and
   exported as STEP using ``parapy.exchange.step.STEPWriter``.

Note: The STL→STEP conversion is approximate (fitted B-Rep), because
      OpenCascade cannot represent implicit TPMS surfaces exactly.
"""

from __future__ import annotations

import os
import struct
from math import atan2
from pathlib import Path

from parapy.core import Base, Input, Attribute, Part
from parapy.core.validate import Range
from parapy.exchange.step import STEPWriter


class GeometryExportService(Base):
    """Reads an STL and provides a ParaPy STEPWriter Part."""

    #: Path to the downloaded STL file
    stl_path: str = Input("")

    #: Directory where STEP / STL outputs are saved
    output_dir: str = Input("outputs")

    #: Base filename (no extension)
    output_name: str = Input("heat_exchanger")

    #: Number of slicing planes for contour extraction
    n_slices: int = Input(20, validator=Range(4, 200))

    #: BSpline degree for contour curves
    bspline_degree: int = Input(3, validator=Range(1, 7))

    # ── derived ──────────────────────────────────────────────────────

    @Attribute
    def step_path(self) -> str:
        return str(Path(self.output_dir) / f"{self.output_name}.stp")

    @Attribute
    def stl_available(self) -> bool:
        p = Path(self.stl_path)
        return p.is_file() and p.stat().st_size > 0

    # ── STEP writer as a @Part (follows tutorial pattern) ────────────

    @Part
    def step_writer(self):
        """STEPWriter that exports the encapsulation tree.

        Fire the ``write`` method via the ParaPy GUI to produce the STEP.
        The ``trees`` input is set dynamically by ``write_assembly()``.
        """
        return STEPWriter(
            default_directory=self.output_dir,
            trees=[],   # populated by write_assembly()
        )

    # ── public actions ───────────────────────────────────────────────

    def write_assembly(self, *geom_nodes) -> str:
        """Export one or more ParaPy geometry nodes to STEP.

        Parameters
        ----------
        *geom_nodes
            ParaPy geometry objects (e.g. ``encapsulation.shell``).

        Returns
        -------
        str — path to the STEP file.
        """
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        writer = STEPWriter(
            nodes=list(geom_nodes),
            default_directory=self.output_dir,
        )
        writer.write()
        return self.step_path

    def reconstruct_lattice(self):
        """Read the STL and return a list of ParaPy BSplineCurve profiles.

        These can be passed to ``LoftedShell(profiles=…)`` or
        ``LoftedSurface(profiles=…)`` to create a B-Rep approximation
        of the lattice surface.

        Returns
        -------
        list[parapy.geom.BSplineCurve]
        """
        if not self.stl_available:
            raise FileNotFoundError(
                f"STL not found at '{self.stl_path}'.  "
                f"Download it first via SimulationConnector.download_stl()."
            )
        verts, faces = _read_stl(self.stl_path)
        return _slice_and_fit(verts, faces,
                              n_slices=self.n_slices,
                              degree=self.bspline_degree)


# ─────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────

def _read_stl(path: str):
    """Minimal STL reader (ASCII + binary).

    Returns
    -------
    verts : list[(float, float, float)]
    faces : list[(int, int, int)]   — indices into *verts*
    """
    verts: list[tuple[float, float, float]] = []
    faces: list[tuple[int, int, int]] = []
    vmap: dict[tuple, int] = {}

    def _idx(v):
        if v not in vmap:
            vmap[v] = len(verts)
            verts.append(v)
        return vmap[v]

    raw = Path(path).read_bytes()

    if raw[:5] == b"solid" and b"\n" in raw[:80]:
        # ── ASCII ────────────────────────────────────────────────────
        tri: list[tuple[float, float, float]] = []
        for line in raw.decode(errors="replace").splitlines():
            tok = line.strip()
            if tok.startswith("vertex"):
                parts = tok.split()
                v = (float(parts[1]), float(parts[2]), float(parts[3]))
                tri.append(v)
                if len(tri) == 3:
                    faces.append((_idx(tri[0]), _idx(tri[1]), _idx(tri[2])))
                    tri = []
    else:
        # ── binary ───────────────────────────────────────────────────
        n_tri = struct.unpack_from("<I", raw, 80)[0]
        off = 84
        for _ in range(n_tri):
            off += 12  # skip normal
            tri_v = []
            for _ in range(3):
                v = struct.unpack_from("<fff", raw, off)
                off += 12
                tri_v.append(v)
            off += 2  # attribute
            faces.append((_idx(tri_v[0]), _idx(tri_v[1]), _idx(tri_v[2])))

    return verts, faces


def _slice_and_fit(verts, faces, *, n_slices: int, degree: int):
    """Intersect mesh with X-perpendicular planes, fit BSplines."""
    from parapy.geom import BSplineCurve, Point

    xs = [v[0] for v in verts]
    x_lo, x_hi = min(xs), max(xs)
    dx = (x_hi - x_lo) / (n_slices + 1)

    curves = []
    for i in range(1, n_slices + 1):
        x_cut = x_lo + i * dx
        pts = _plane_intersect(verts, faces, x_cut)
        if len(pts) < 4:
            continue
        pp = [Point(*p) for p in pts]
        try:
            curves.append(BSplineCurve(points=pp, degree=degree,
                                       closed=True))
        except Exception:
            pass  # skip degenerate slices

    if len(curves) < 2:
        raise RuntimeError(
            f"Only {len(curves)} valid contour(s) from STL.  "
            f"Try increasing n_slices or check mesh quality."
        )
    return curves


def _plane_intersect(verts, faces, x_val: float):
    """Return sorted (x, y, z) points where faces cross x = x_val."""
    pts: list[tuple[float, float, float]] = []
    for f in faces:
        tv = [verts[i] for i in f]
        edge_pts: list[tuple[float, float, float]] = []
        for j in range(3):
            a, b = tv[j], tv[(j + 1) % 3]
            if (a[0] <= x_val <= b[0]) or (b[0] <= x_val <= a[0]):
                dx = b[0] - a[0]
                if abs(dx) < 1e-15:
                    continue
                t = (x_val - a[0]) / dx
                y = a[1] + t * (b[1] - a[1])
                z = a[2] + t * (b[2] - a[2])
                edge_pts.append((x_val, y, z))
            if len(edge_pts) == 2:
                break
        pts.extend(edge_pts)

    if not pts:
        return pts
    # Sort by angle around centroid for a proper contour ordering
    cy = sum(p[1] for p in pts) / len(pts)
    cz = sum(p[2] for p in pts) / len(pts)
    pts.sort(key=lambda p: atan2(p[2] - cz, p[1] - cy))
    # De-duplicate
    uniq = [pts[0]]
    for p in pts[1:]:
        if abs(p[1] - uniq[-1][1]) > 1e-9 or abs(p[2] - uniq[-1][2]) > 1e-9:
            uniq.append(p)
    return uniq
