"""
optimization_history.py
-----------------------
Tracks the optimisation run: polls the gRPC server for per-iteration
metrics and stores them for convergence plotting and the PDF report.

Maps to UML classes: **OptimizationManager**, **OptimizationHistory**

The MTO server streams metrics (outlet temperature, mechanical
dissipation, objective, constraint violations) as the optimiser runs.
This class parses the ``history`` / ``latest`` output from ``client.py``
into structured records.
"""

from __future__ import annotations

import json
import re

from parapy.core import Base, Input, Attribute


class OptimizationHistory(Base):
    """Parses and stores optimiser iteration history.

    ``raw_history`` is the text returned by ``SimulationConnector.optimisation_history``
    (i.e. ``client.py history``).  The server emits one JSON object per
    iteration; this class extracts the numeric series for plotting.
    """

    #: Raw text dump from ``client.py history``
    raw_history: str = Input("")

    @Attribute
    def records(self) -> list[dict]:
        """List of per-iteration dicts parsed from the raw history.

        ``client.py history`` emits **tab-separated values** with a header
        row, so TSV is tried first.  JSON (array / json-lines) and a regex
        key=value scrape are kept as fallbacks for robustness.
        """
        text = self.raw_history.strip()
        if not text:
            return []

        # ── Primary: TSV (the actual client.py history output) ──────────
        lines = text.splitlines()
        if lines and "\t" in lines[0]:
            headers = [h.strip() for h in lines[0].split("\t")]
            recs = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                vals = line.split("\t")
                row = {}
                for h, v in zip(headers, vals):
                    v = v.strip()
                    if v in ("—", "nan", ""):
                        row[h] = None
                    else:
                        row[h] = _to_float(v)
                recs.append(row)
            if recs:
                return recs

        # ── Fallback: whole-blob JSON (array or object) ─────────────────
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "history" in data:
                return data["history"]
        except json.JSONDecodeError:
            pass

        # ── Fallback: json-lines ────────────────────────────────────────
        recs = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        if recs:
            return recs

        # ── Last resort: regex key=value scrape, one record per line ────
        recs = []
        for line in text.splitlines():
            kv = dict(re.findall(r"(\w+)\s*[=:]\s*([-\d.eE+]+)", line))
            if kv:
                recs.append({k: _to_float(v) for k, v in kv.items()})
        return recs

    @Attribute
    def n_iterations(self) -> int:
        return len(self.records)

    def series(self, key: str) -> list[float]:
        """Extract a numeric series for one metric across all iterations."""
        out = []
        for r in self.records:
            if key in r and r[key] is not None:
                out.append(_to_float(r[key]))
        return out

    def series_fuzzy(self, *candidates: str) -> list[float]:
        """Find a series by exact, case-insensitive, then substring match.

        The MTO server's exact column names aren't known ahead of time, so
        this tries progressively looser matching across the record keys.
        """
        recs = self.records
        if not recs:
            return []
        keys = list(recs[0].keys())
        # exact
        for c in candidates:
            if c in keys:
                s = self.series(c)
                if s:
                    return s
        # case-insensitive
        lower = {k.lower(): k for k in keys}
        for c in candidates:
            if c.lower() in lower:
                s = self.series(lower[c.lower()])
                if s:
                    return s
        # substring
        for c in candidates:
            for k in keys:
                if c.lower() in k.lower():
                    s = self.series(k)
                    if s:
                        return s
        return []

    @Attribute
    def iterations(self) -> list[int]:
        return list(range(1, self.n_iterations + 1))

    @Attribute
    def outlet_temperature(self) -> list[float]:
        return self.series_fuzzy("outletT", "outlet_temperature", "outlet_T",
                                 "T_out", "Tout", "temperature", "T_outlet")

    @Attribute
    def mean_temperature(self) -> list[float]:
        return self.series_fuzzy("meantT", "meanT", "MeanT", "mean_temperature",
                                 "constraint", "g_meanT", "T_mean")

    @Attribute
    def mechanical_dissipation(self) -> list[float]:
        return self.series_fuzzy("mechanical_dissipation", "mech_dissipation",
                                 "dissipation", "power", "pressure_drop", "dp")

    @Attribute
    def objective(self) -> list[float]:
        return self.series_fuzzy("objective", "obj", "cost", "J", "loss")

    @Attribute
    def g_oh(self) -> list[float]:
        return self.series_fuzzy("g_oh", "G_oh", "overhang_constraint", "overhang")

    @Attribute
    def latest(self) -> dict:
        return self.records[-1] if self.records else {}

    @Attribute
    def has_converged(self) -> bool:
        """Rough convergence check: objective change < 1% over last 3 iters."""
        obj = self.objective
        if len(obj) < 4:
            return False
        recent = obj[-3:]
        spread = max(recent) - min(recent)
        ref = abs(obj[-1]) + 1e-12
        return (spread / ref) < 0.01


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return v
