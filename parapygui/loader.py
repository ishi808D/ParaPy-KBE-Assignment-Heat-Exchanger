"""
loader.py
---------
Handles loading of external input files:

1. **requirements.json**  — top-level design requirements and operating point
2. **materials.xlsx**     — material properties and LPBF machine constraints

Maps to UML class: **Loader**

Both files are optional.  If they don't exist, HeatExchanger uses its
built-in defaults (air-cooled Ti-6Al-4V gyroid, matching the MTC brief).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from parapy.core import Base, Input, Attribute


class Loader(Base):
    """Load and validate external input files.

    After instantiation, access ``requirements`` and ``materials`` to get
    the parsed data.  ``errors`` collects any parse / validation problems
    so the GUI can surface them all at once.
    """

    #: Path to the JSON requirements file
    json_path: str = Input("inputs/requirements.json")

    #: Path to the Excel material/machine constraints file
    xlsx_path: str = Input("inputs/materials.xlsx")

    # ── JSON ─────────────────────────────────────────────────────────

    @Attribute
    def requirements(self) -> dict[str, Any]:
        """Parsed JSON requirements.  Returns ``{}`` if the file is missing."""
        p = Path(self.json_path)
        if not p.is_file():
            return {}
        try:
            with open(p) as f:
                data = json.load(f)
            # Strip comments
            return {k: v for k, v in data.items() if not k.startswith("_")}
        except (json.JSONDecodeError, OSError) as exc:
            return {"_error": str(exc)}

    @Attribute
    def json_available(self) -> bool:
        return Path(self.json_path).is_file()

    # ── Excel ────────────────────────────────────────────────────────

    @Attribute
    def materials(self) -> list[dict[str, Any]]:
        """List of material rows from the first sheet of the xlsx.

        Each row becomes a dict keyed by column header.
        Returns ``[]`` if the file is missing or openpyxl is not installed.
        """
        p = Path(self.xlsx_path)
        if not p.is_file():
            return []
        try:
            import openpyxl
        except ImportError:
            return [{"_error": "openpyxl not installed"}]

        try:
            wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
            ws = wb.active
            rows = list(ws.iter_rows(values_only=True))
            wb.close()
            if len(rows) < 2:
                return []
            headers = [str(h).strip() for h in rows[0]]
            return [
                {h: cell for h, cell in zip(headers, row)}
                for row in rows[1:]
            ]
        except Exception as exc:
            return [{"_error": str(exc)}]

    @Attribute
    def xlsx_available(self) -> bool:
        return Path(self.xlsx_path).is_file()

    # ── convenience ──────────────────────────────────────────────────

    @Attribute
    def errors(self) -> list[str]:
        """Collect all loading errors."""
        errs: list[str] = []
        req = self.requirements
        if "_error" in req:
            errs.append(f"JSON load error: {req['_error']}")
        for row in self.materials:
            if "_error" in row:
                errs.append(f"Excel load error: {row['_error']}")
        return errs

    def get(self, key: str, default=None):
        """Look up a value from the requirements JSON with a fallback."""
        return self.requirements.get(key, default)
