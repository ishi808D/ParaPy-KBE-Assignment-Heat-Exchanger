"""
main.py
-------
Entry point for the Bio-Inspired Heat Exchanger KBE application.

Usage
~~~~~
    # Open the ParaPy GUI with defaults
    python -m parapygui.main

    # Load from a JSON config file
    python -m parapygui.main --config inputs/requirements.json

    # Print the design summary without opening the GUI (CI / testing)
    python -m parapygui.main --no-gui

The GUI shows three panels:
    • Product tree (left)      — HeatExchanger and all sub-parts
    • Property grid (left)     — all @Input slots, editable in real time
    • Viewport (right)         — encapsulation shell geometry, auto-updates
"""

import argparse
import json
import sys
from pathlib import Path


def _build(config_path: str | None):
    """Instantiate the root HeatExchanger."""
    from heat_exchanger import HeatExchanger

    if config_path and Path(config_path).is_file():
        print(f"Loading config: {config_path}")
        obj = HeatExchanger.from_json(config_path)
    else:
        if config_path:
            print(f"Config file not found: {config_path}  — using defaults.")
        obj = HeatExchanger(label="Bio-Inspired Heat Exchanger")

    # Report validation
    errs = obj.validation_errors
    if errs:
        print(f"⚠  {len(errs)} validation issue(s):")
        for e in errs:
            print(f"   • {e}")
    else:
        print("✓  All validation checks passed.")

    return obj


def main():
    ap = argparse.ArgumentParser(
        description="Bio-Inspired Heat Exchanger KBE App (ParaPy)")
    ap.add_argument("--config", "-c",
                    default="inputs/requirements.json",
                    help="Path to requirements JSON  (default: inputs/requirements.json)")
    ap.add_argument("--no-gui", action="store_true",
                    help="Print design summary to stdout; don't open the GUI")
    args = ap.parse_args()

    obj = _build(args.config)

    if args.no_gui:
        print("\n── Design Summary ──")
        print(json.dumps(obj.design_summary, indent=2))
        return

    from parapy.gui import display
    display(obj)


if __name__ == "__main__":
    main()
