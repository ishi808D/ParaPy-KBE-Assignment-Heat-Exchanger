"""
reporting.py
------------
Output reporting: design-summary PDF + CFD convergence plots (PNG/PDF).

Maps to UML output capabilities #3 (Design summary report PDF) and
#4 (CFD results output PDF/PNG) from the proposal.

Uses matplotlib only (already a project dependency) so there are no extra
requirements.  The report pulls together:
    * all input parameters and design requirements
    * computed thermal-hydraulic performance (Nu, h, solidity)
    * mass estimate
    * DfAM compliance summary
    * key geometric dimensions
    * optimisation convergence plots (if a history is supplied)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from parapy.core import Base, Input, Attribute


class ReportGenerator(Base):
    """Builds the design-summary PDF and convergence figures."""

    #: Output directory
    output_dir: str = Input("outputs")

    #: Base filename (no extension)
    report_name: str = Input("design_report")

    #: design_summary dict from HeatExchanger
    design_summary: dict = Input({})

    #: manufacturability summary dict
    manufacturability_summary: dict = Input({})

    #: optimisation history object (optional) — must expose iterations,
    #: outlet_temperature, mechanical_dissipation, objective
    history: object = Input(None)

    @Attribute
    def pdf_path(self) -> str:
        return str(Path(self.output_dir) / f"{self.report_name}.pdf")

    @Attribute
    def convergence_png_path(self) -> str:
        return str(Path(self.output_dir) / f"{self.report_name}_convergence.png")

    # ── actions ──────────────────────────────────────────────────────

    def generate(self) -> str:
        """Produce the full multi-page PDF report.  Returns the path."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        with PdfPages(self.pdf_path) as pdf:
            self._page_summary(plt, pdf)
            if self.history is not None and getattr(self.history,
                                                    "n_iterations", 0) > 0:
                self._page_convergence(plt, pdf)
        return self.pdf_path

    def generate_convergence_png(self) -> str:
        """Standalone convergence PNG (proposal output #4)."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        fig = self._convergence_figure(plt)
        if fig is None:
            return ""
        fig.savefig(self.convergence_png_path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return self.convergence_png_path

    # ── page builders ────────────────────────────────────────────────

    def _page_summary(self, plt, pdf):
        """Text page: all parameters and computed performance."""
        fig = plt.figure(figsize=(8.27, 11.69))   # A4 portrait
        fig.suptitle("Bio-Inspired Heat Exchanger — Design Summary",
                     fontsize=15, fontweight="bold", y=0.98)

        lines = [f"Generated: {datetime.now():%Y-%m-%d %H:%M}", ""]
        lines += self._dict_to_lines(self.design_summary)
        if self.manufacturability_summary:
            lines += ["", "── Manufacturability ──"]
            lines += self._dict_to_lines(self.manufacturability_summary)

        fig.text(0.07, 0.92, "\n".join(lines), va="top", ha="left",
                 family="monospace", fontsize=9)
        pdf.savefig(fig)
        plt.close(fig)

    def _page_convergence(self, plt, pdf):
        fig = self._convergence_figure(plt)
        if fig is not None:
            pdf.savefig(fig)
            plt.close(fig)

    def _convergence_figure(self, plt):
        h = self.history
        it = getattr(h, "iterations", [])
        if not it:
            return None
        outT = getattr(h, "outlet_temperature", [])
        mech = getattr(h, "mechanical_dissipation", [])
        obj = getattr(h, "objective", [])

        n_panels = sum(bool(s) for s in (outT, mech, obj)) or 1
        fig, axes = plt.subplots(n_panels, 1,
                                 figsize=(8.27, 3.2 * n_panels),
                                 squeeze=False)
        axes = axes[:, 0]
        idx = 0
        for series, label, color in [
            (outT, "Outlet Temperature [K]", "tab:blue"),
            (mech, "Mechanical Dissipation [W]", "tab:red"),
            (obj,  "Objective [-]", "tab:green"),
        ]:
            if not series:
                continue
            ax = axes[idx]
            ax.plot(it[:len(series)], series, "-o", ms=3, color=color)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(label)
            ax.set_title(label.split(" [")[0] + " Convergence")
            ax.grid(True, alpha=0.3)
            idx += 1
        fig.tight_layout()
        return fig

    @staticmethod
    def _dict_to_lines(d: dict, indent: int = 0) -> list[str]:
        """Flatten a nested dict into aligned text lines."""
        out = []
        pad = "  " * indent
        for k, v in d.items():
            if isinstance(v, dict):
                out.append(f"{pad}{k}:")
                out += ReportGenerator._dict_to_lines(v, indent + 1)
            else:
                out.append(f"{pad}{k:.<34} {v}")
        return out
