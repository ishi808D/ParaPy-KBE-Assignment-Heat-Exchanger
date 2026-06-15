"""
validators.py
-------------
Cross-parameter validation that cannot be expressed as single-slot
``parapy.core.validate.Range`` checks.

Each function raises ``ValueError`` with a descriptive message.
``validate_heat_exchanger()`` collects them all into a list so the
GUI can show every problem at once.
"""

from __future__ import annotations


def check_interior_positive(length, width, height, wt) -> None:
    """Wall thickness must leave a positive interior cavity."""
    for name, outer in [("length", length), ("width", width), ("height", height)]:
        inner = outer - 2 * wt
        if inner <= 0:
            raise ValueError(
                f"wall_thickness ({wt*1e3:.1f} mm) too large: "
                f"interior {name} becomes {inner*1e3:.1f} mm."
            )


def check_tube_fits(width, height, wt, bore_w, bore_h, tube_wt) -> None:
    """Port tube must fit within the interior face."""
    face_min = min(width - 2*wt, height - 2*wt)
    tube_outer = max(bore_w, bore_h) + 2 * tube_wt
    if tube_outer >= face_min:
        raise ValueError(
            f"Tube outer size ({tube_outer*1e3:.1f} mm) exceeds "
            f"smallest interior face dimension ({face_min*1e3:.1f} mm)."
        )


def check_temperatures(t_in, t_ext) -> None:
    """Inflow must be hotter than exterior for a cooling application."""
    if t_in <= t_ext:
        raise ValueError(
            f"inflow_temperature ({t_in:.1f} K) must exceed "
            f"exterior_temperature ({t_ext:.1f} K)."
        )


def check_dissipation_bounds(lo, hi) -> None:
    if lo >= hi:
        raise ValueError(
            f"mech_dissipation lower ({lo}) must be < upper ({hi})."
        )


def check_build_volume(length, width, height, bv) -> None:
    """Encapsulation must fit inside the LPBF build volume."""
    if length > bv[0] or width > bv[1] or height > bv[2]:
        raise ValueError(
            f"Encapsulation ({length*1e3:.0f}×{width*1e3:.0f}×"
            f"{height*1e3:.0f} mm) exceeds build volume "
            f"({bv[0]*1e3:.0f}×{bv[1]*1e3:.0f}×{bv[2]*1e3:.0f} mm)."
        )


def check_wall_vs_feature(wall_t, min_feat) -> None:
    if wall_t < min_feat:
        raise ValueError(
            f"wall_thickness ({wall_t*1e3:.3f} mm) is below the "
            f"minimum feature size ({min_feat*1e3:.3f} mm)."
        )


# ─────────────────────────────────────────────────────────────────────
# Master validator
# ─────────────────────────────────────────────────────────────────────

def validate_heat_exchanger(he) -> list[str]:
    """Run all cross-checks.  Returns a list of error strings (empty = OK).

    ``he`` is a HeatExchanger instance.
    """
    errors: list[str] = []
    enc = he.encapsulation
    env = he.environment
    mfg = he.manufacturing
    checks = [
        (check_interior_positive,
         (enc.length, enc.width, enc.height, enc.wall_thickness)),
        (check_tube_fits,
         (enc.width, enc.height, enc.wall_thickness,
                    enc.inlet_bore_width, enc.inlet_bore_height, enc.tube_wall)),
        (check_temperatures,
         (env.inflow_temperature, env.exterior_temperature)),
        (check_dissipation_bounds,
         (env.mech_dissipation_lower, env.mech_dissipation_upper)),
        (check_build_volume,
         (enc.length, enc.width, enc.height, mfg.build_volume)),
        (check_wall_vs_feature,
         (enc.wall_thickness, mfg.min_feature_size)),
    ]
    for fn, args in checks:
        try:
            fn(*args)
        except ValueError as exc:
            errors.append(str(exc))
    return errors
