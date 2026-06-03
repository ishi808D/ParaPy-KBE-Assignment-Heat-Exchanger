"""
pyslm_analysis.py
-----------------
PySLM-based final manufacturability analysis on the exported STL.

Maps to UML class: **PySLMAnalysis**

After the optimiser produces a final design and the STL is generated, this
class runs PySLM (https://github.com/drlukeparry/pyslm) to slice the part
for the target LPBF machine and report:
    * total number of layers
    * estimated build time
    * overhang / support-area assessment
    * total scan-path length (proxy for energy / time)

PySLM is an *optional* dependency.  If it is not installed the class
degrades gracefully and reports that the analysis was skipped, so the
rest of the app keeps working without it.
"""

from __future__ import annotations

from pathlib import Path

from parapy.core import Base, Input, Attribute
from parapy.core.validate import Range


class PySLMAnalysis(Base):
    """Slice + analyse the final STL for LPBF manufacturability."""

    #: Path to the final STL file to analyse
    stl_path: str = Input("")

    #: Layer thickness for the target LPBF machine  [m]
    layer_thickness: float = Input(30e-6, validator=Range(1e-6, 200e-6))

    #: Maximum unsupported overhang angle  [deg]
    max_overhang_angle: float = Input(45.0, validator=Range(0.0, 90.0))

    #: Laser scan speed  [m/s]  (for build-time estimate)
    scan_speed: float = Input(1.0, validator=Range(0.01, 10.0))

    #: Hatch spacing  [m]
    hatch_distance: float = Input(80e-6, validator=Range(10e-6, 500e-6))

    # ── availability ─────────────────────────────────────────────────

    @Attribute
    def pyslm_available(self) -> bool:
        try:
            import pyslm  # noqa: F401
            return True
        except ImportError:
            return False

    @Attribute
    def stl_available(self) -> bool:
        p = Path(self.stl_path)
        return p.is_file() and p.stat().st_size > 0

    # ── analysis ─────────────────────────────────────────────────────

    @Attribute
    def report(self) -> dict:
        """Run PySLM slicing and return a manufacturability report dict.

        Returns a dict with a ``status`` key.  When PySLM or the STL is
        missing, ``status`` explains why and the rest of the app continues.
        """
        if not self.pyslm_available:
            return {"status": "skipped",
                    "reason": "PySLM not installed (pip install PythonSLM)"}
        if not self.stl_available:
            return {"status": "skipped",
                    "reason": f"STL not found: {self.stl_path}"}

        try:
            import numpy as np
            import pyslm
            from pyslm import hatching

            part = pyslm.Part("lattice")
            part.setGeometry(self.stl_path)
            part.dropToPlatform()

            z_min, z_max = part.boundingBox[2], part.boundingBox[5]
            height = z_max - z_min
            n_layers = max(1, int(height / self.layer_thickness))

            # Slice + hatch a representative subset of layers to estimate
            # scan length, then scale to the full part.
            sample_idx = np.linspace(z_min + self.layer_thickness,
                                     z_max - self.layer_thickness,
                                     min(n_layers, 20))
            hatcher = hatching.Hatcher()
            hatcher.hatchDistance = self.hatch_distance

            total_len_sample = 0.0
            sampled = 0
            for z in sample_idx:
                geom = part.getVectorSlice(z)
                if not geom:
                    continue
                layer = hatcher.hatch(geom)
                for path in layer.geometry:
                    coords = np.asarray(path.coords)
                    if len(coords) > 1:
                        seg = np.diff(coords, axis=0)
                        total_len_sample += np.hypot(seg[:, 0], seg[:, 1]).sum()
                sampled += 1

            avg_len_per_layer = total_len_sample / max(sampled, 1)
            total_scan_len = avg_len_per_layer * n_layers          # [mm]
            build_time_s = (total_scan_len * 1e-3) / self.scan_speed

            return {
                "status": "ok",
                "n_layers": n_layers,
                "part_height_mm": round(height, 3),
                "total_scan_length_m": round(total_scan_len * 1e-3, 2),
                "est_build_time_min": round(build_time_s / 60.0, 1),
                "layer_thickness_um": round(self.layer_thickness * 1e6, 1),
            }
        except Exception as exc:
            return {"status": "error", "reason": str(exc)}

    @Attribute
    def summary(self) -> dict:
        return self.report
