"""
manufacturability.py
--------------------
Design-for-Additive-Manufacturing analysis of a lattice mesh.

Maps to UML classes: **ManufacturingConstraintSet** (penalty side),
implements the methods from doi:10.1016/j.ijheatmasstransfer.2024.126299.

Two checks:
  1. **Overhang** — triangles whose downward-facing normal exceeds the
     maximum unsupported overhang angle need support structures.
  2. **Wall thickness** — estimated from solidity and unit-cell size;
     flagged if below the machine minimum feature size.

The combined ``penalty`` is what gets fed back to the optimiser so it
converges towards a printable design.  This is an *internal* analysis on
the gamma/voxel field (distinct from the final PySLM check on the STL).
"""

from __future__ import annotations

from math import cos, radians, pi

import numpy as np

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class ManufacturabilityAnalysis(Base):
    """Overhang + wall-thickness manufacturability score for a GyroidMesh."""

    # ── mesh inputs (set from the GyroidMesh part) ───────────────────

    #: face normals  (N,3) numpy array
    face_normals: object = Input()

    #: face areas    (N,) numpy array  (for area-weighted penalty)
    face_areas: object = Input()

    #: current solidity  [-]
    solidity: float = Input()

    #: mean unit-cell size  [m]
    unit_cell_size: float = Input()

    # ── machine constraints ──────────────────────────────────────────

    #: build direction unit vector  (default +Z)
    build_direction: tuple = Input((0.0, 0.0, 1.0))

    #: maximum unsupported overhang from vertical  [deg]
    max_overhang_angle: float = Input(45.0, validator=Range(0.0, 90.0))

    #: minimum printable feature size  [m]
    min_feature_size: float = Input(2e-4, validator=Range(5e-5, 5e-3))

    #: weight balancing overhang vs. thickness penalties
    overhang_weight: float = Input(1.0)
    thickness_weight: float = Input(1.0)

    # ── overhang ─────────────────────────────────────────────────────

    @Attribute
    def downfacing_mask(self):
        """Boolean mask of triangles facing away from the build direction."""
        n = np.asarray(self.face_normals)
        bd = np.asarray(self.build_direction, dtype=float)
        bd = bd / np.linalg.norm(bd)
        return n.dot(bd) < 0.0

    @Attribute
    def overhang_violating_mask(self):
        """Triangles steeper than the max overhang angle (need support).

        A downward face violates when the angle between its normal and the
        downward build axis is small (normal points straight down).
        Threshold: n·(−bd) > cos(90° − max_overhang).
        """
        n = np.asarray(self.face_normals)
        bd = np.asarray(self.build_direction, dtype=float)
        bd = bd / np.linalg.norm(bd)
        downness = n.dot(-bd)                       # 1 = straight down
        threshold = cos(radians(90.0 - self.max_overhang_angle))
        return downness > threshold

    @Attribute
    def overhang_penalty(self) -> float:
        """Area-weighted fraction of overhang-violating surface  [0..1]."""
        areas = np.asarray(self.face_areas)
        mask = self.overhang_violating_mask
        total = areas.sum()
        if total <= 0:
            return 0.0
        return float(areas[mask].sum() / total)

    # ── wall thickness ───────────────────────────────────────────────

    @Attribute
    def estimated_wall_thickness(self) -> float:
        """Approximate wall thickness from solidity & unit-cell size  [m].
        For a sheet-TPMS:  t ≈ solidity · unit_cell / π.
        """
        if self.unit_cell_size == float("inf"):
            return 0.0
        return self.solidity * self.unit_cell_size / pi

    @Attribute
    def thickness_penalty(self) -> float:
        """Penalty when wall thickness drops below min feature size  [0..1].
        Linear ramp: 0 at/above min feature, 1 at zero thickness.
        """
        t = self.estimated_wall_thickness
        if t >= self.min_feature_size:
            return 0.0
        return float(1.0 - t / self.min_feature_size)

    # ── combined ─────────────────────────────────────────────────────

    @Attribute
    def penalty(self) -> float:
        """Combined manufacturability penalty fed back to the optimiser."""
        return (self.overhang_weight * self.overhang_penalty +
                self.thickness_weight * self.thickness_penalty)

    @Attribute
    def is_printable(self) -> bool:
        """True if no constraint is meaningfully violated."""
        return self.overhang_penalty < 0.05 and self.thickness_penalty == 0.0

    @Attribute
    def summary(self) -> dict:
        return {
            "overhang_penalty":          round(self.overhang_penalty, 4),
            "thickness_penalty":         round(self.thickness_penalty, 4),
            "combined_penalty":          round(self.penalty, 4),
            "est_wall_thickness_mm":     round(self.estimated_wall_thickness * 1e3, 4),
            "min_feature_size_mm":       round(self.min_feature_size * 1e3, 4),
            "max_overhang_angle_deg":    self.max_overhang_angle,
            "printable":                 self.is_printable,
        }
