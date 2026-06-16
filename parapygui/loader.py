"""
loader.py
---------
Handles loading of external input files:

1. **requirements.json**  — top-level design requirements and operating point

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

    After instantiation, access ``requirements`` to get the parsed data.  ``errors`` collects any parse / validation problems
    so the GUI can surface them all at once.
    """

    #: Path to the JSON requirements file
    json_path: str = Input("inputs/requirements.json")


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


    # ── convenience ──────────────────────────────────────────────────

    @Attribute
    def errors(self) -> list[str]:
        """Collect all loading errors."""
        errs: list[str] = []
        req = self.requirements
        if "_error" in req:
            errs.append(f"JSON load error: {req['_error']}")
        return errs

    def get(self, key: str, default=None):
        """Look up a value from the requirements JSON with a fallback."""
        return self.requirements.get(key, default)
