"""
reporting.py
------------
Output reporting: design-summary PDF + geometry images + optimisation history.

Pages generated:
  1. Design summary (parameters + performance text)
  2. Geometry — PyVista off-screen renders of each downloaded STL
  3. Optimisation history table (one row per iteration)
  4. Convergence plots (outlet T, dissipation, objective vs iteration)
"""

from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from parapy.core import Base, Input, Attribute


class ReportGenerator(Base):
    """Builds the multi-page design report PDF."""

    output_dir:  str  = Input("outputs")
    report_name: str  = Input("design_report")

    design_summary:            dict   = Input({})
    manufacturability_summary: dict   = Input({})

    # STL files to render as geometry screenshots
    stl_paths: list = Input([])

    # Optimisation history — from wizard's live-parsed data
    opt_iters: list = Input([])
    opt_objs:  list = Input([])
    opt_cstrs: list = Input([])
    opt_g_oh:  list = Input([])

    # Full history table from gRPC GetHistory (preferred when available)
    history_columns: list = Input([])
    history_rows:    list = Input([])   # list of dicts {col_name: float}

    # Legacy: OptimizationHistory object (used for convergence plots)
    history: object = Input(None)

    @Attribute
    def pdf_path(self) -> str:
        return str(Path(self.output_dir) / f"{self.report_name}.pdf")

    # ── public API ────────────────────────────────────────────────────

    def generate(self) -> str:
        """Produce the full multi-page PDF. Returns the path."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)

        with PdfPages(self.pdf_path) as pdf:
            self._page_summary(plt, pdf)
            if self.stl_paths:
                self._page_geometry(plt, pdf)
            if self.history_rows or self.opt_iters:
                self._page_history_table(plt, pdf)
            if self.history is not None and getattr(self.history, "n_iterations", 0) > 0:
                self._page_convergence(plt, pdf)
            elif self.opt_iters:
                self._page_convergence_from_lists(plt, pdf)
            elif self.history_rows:
                self._page_convergence_from_rows(plt, pdf)

        return self.pdf_path

    def generate_convergence_png(self) -> str:
        """Standalone convergence PNG."""
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        fig = self._convergence_figure(plt)
        if fig is None:
            return ""
        out = str(Path(self.output_dir) / f"{self.report_name}_convergence.png")
        fig.savefig(out, dpi=150, bbox_inches="tight")
        plt.close(fig)
        return out

    # ── page builders ─────────────────────────────────────────────────

    def _page_summary(self, plt, pdf):
        lines = [f"Generated: {datetime.now():%Y-%m-%d %H:%M}", ""]
        lines += self._dict_to_lines(self.design_summary)
        if self.manufacturability_summary:
            lines += ["", "── Manufacturability ──"]
            lines += self._dict_to_lines(self.manufacturability_summary)

        # A4 body available after title (y 0.92 → 0.01, ~0.91 of 11.69 in = 10.64 in).
        # Line height = fontsize * 1.2 / 72.  Fit everything into [5.5, 9] pt;
        # if still too many lines, paginate at the clamped size.
        PAGE_H_IN   = 11.69
        TEXT_FRAC   = 0.91          # fraction of page available for text lines
        LEAD        = 1.2           # line-height multiplier
        MAX_FS      = 9.0
        MIN_FS      = 5.5

        avail_in = PAGE_H_IN * TEXT_FRAC
        ideal_fs = avail_in * 72.0 / (max(len(lines), 1) * LEAD)
        fontsize  = max(MIN_FS, min(MAX_FS, ideal_fs))
        lpp       = int(avail_in * 72.0 / (fontsize * LEAD))  # lines per page

        chunks = [lines[i:i + lpp] for i in range(0, len(lines), lpp)]
        n_pages = len(chunks)

        for page_idx, chunk in enumerate(chunks):
            fig = plt.figure(figsize=(8.27, PAGE_H_IN))
            title = "Bio-Inspired Heat Exchanger — Design Summary"
            if n_pages > 1:
                title += f"  ({page_idx + 1} / {n_pages})"
            fig.suptitle(title, fontsize=15, fontweight="bold", y=0.98)
            fig.text(0.07, 0.92, "\n".join(chunk), va="top", ha="left",
                     family="monospace", fontsize=fontsize)
            pdf.savefig(fig)
            plt.close(fig)

    def _page_geometry(self, plt, pdf):
        """Render each STL with PyVista and embed as an image per row."""
        screenshots = []
        for path in self.stl_paths:
            img = self._pyvista_screenshot(path)
            if img is not None:
                screenshots.append((Path(path).name, img))

        if not screenshots:
            return

        n = len(screenshots)
        fig, axes = plt.subplots(n, 1, figsize=(8.27, 5.0 * n), squeeze=False)
        fig.suptitle("Optimised Geometry", fontsize=14, fontweight="bold")

        for ax, (fname, img_bytes) in zip(axes[:, 0], screenshots):
            import numpy as np
            from PIL import Image
            import io
            arr = np.array(Image.open(io.BytesIO(img_bytes)))
            ax.imshow(arr)
            ax.set_title(fname, fontsize=10)
            ax.axis("off")

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        pdf.savefig(fig)
        plt.close(fig)

    def _page_history_table(self, plt, pdf):
        """Render the optimisation history as a formatted table."""
        # Prefer full gRPC history; fall back to wizard's live-parsed lists
        if self.history_rows and self.history_columns:
            cols = self.history_columns
            rows = [[f"{r.get(c, ''):.4g}" if isinstance(r.get(c), float)
                     else str(r.get(c, ""))
                     for c in cols]
                    for r in self.history_rows]
        elif self.opt_iters:
            cols = ["Iteration", "Objective", "Constraint"]
            rows = []
            for i, it in enumerate(self.opt_iters):
                obj  = f"{self.opt_objs[i]:.4g}"  if i < len(self.opt_objs)  else "—"
                cstr = f"{self.opt_cstrs[i]:.4g}" if i < len(self.opt_cstrs) else "—"
                rows.append([str(it), obj, cstr])
        else:
            return

        # Limit rows per page to avoid an unreadable wall of text
        rows_per_page = 40
        for page_start in range(0, len(rows), rows_per_page):
            page_rows = rows[page_start:page_start + rows_per_page]
            fig, ax = plt.subplots(figsize=(8.27, 11.69))
            ax.axis("off")

            title = "Optimisation History"
            if len(rows) > rows_per_page:
                end = min(page_start + rows_per_page, len(rows))
                title += f"  (rows {page_start + 1}–{end} of {len(rows)})"
            fig.suptitle(title, fontsize=13, fontweight="bold")

            tbl = ax.table(
                cellText=page_rows,
                colLabels=cols,
                loc="center",
                cellLoc="center",
            )
            tbl.auto_set_font_size(False)
            tbl.set_fontsize(7)
            tbl.auto_set_column_width(list(range(len(cols))))

            # Header row styling
            for col_idx in range(len(cols)):
                tbl[(0, col_idx)].set_facecolor("#2C3E50")
                tbl[(0, col_idx)].set_text_props(color="white", fontweight="bold")

            # Alternating row colours
            for row_idx in range(1, len(page_rows) + 1):
                colour = "#EAF2FF" if row_idx % 2 == 0 else "white"
                for col_idx in range(len(cols)):
                    tbl[(row_idx, col_idx)].set_facecolor(colour)

            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    def _page_convergence(self, plt, pdf):
        fig = self._convergence_figure(plt)
        if fig is not None:
            pdf.savefig(fig)
            plt.close(fig)

    def _page_convergence_from_lists(self, plt, pdf):
        """Convergence plots built from the wizard's live-parsed data."""
        if not self.opt_iters:
            return
        _nz = lambda s: s if s and any(v != 0.0 for v in s) else []
        panels = [
            (_nz(self.opt_objs),  "Objective",                    "tab:blue"),
            (_nz(self.opt_cstrs), "Mean Temperature Constraint",  "tab:red"),
            (_nz(self.opt_g_oh),  "Overhang Constraint (g_oh)",   "tab:orange"),
        ]
        panels = [(s, l, c) for s, l, c in panels if s]
        if not panels:
            return
        fig, axes = plt.subplots(len(panels), 1,
                                 figsize=(8.27, 3.5 * len(panels)),
                                 squeeze=False)
        fig.suptitle("Convergence History", fontsize=13, fontweight="bold")
        for ax, (series, label, colour) in zip(axes[:, 0], panels):
            ax.plot(self.opt_iters[:len(series)], series,
                    "-o", ms=3, color=colour)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(label)
            ax.set_title(f"{label} Convergence")
            ax.grid(True, alpha=0.3)
            ax.margins(y=0.1)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    def _convergence_figure(self, plt):
        h = self.history
        it = getattr(h, "iterations", [])
        if not it:
            return None
        outT  = getattr(h, "outlet_temperature", [])
        meanT = getattr(h, "mean_temperature", [])
        mech  = getattr(h, "mechanical_dissipation", [])
        obj   = getattr(h, "objective", [])
        goh   = getattr(h, "g_oh", [])
        panels = [(s, l, c) for s, l, c in [
            (outT,  "Outlet Temperature [K]",        "tab:blue"),
            (meanT, "Mean Temperature [K]",           "tab:cyan"),
            (mech,  "Mechanical Dissipation [W]",     "tab:red"),
            (obj,   "Objective [-]",                  "tab:green"),
            (goh,   "Overhang Constraint g_oh [-]",   "tab:orange"),
        ] if s]
        if not panels:
            return None
        fig, axes = plt.subplots(len(panels), 1,
                                 figsize=(8.27, 3.2 * len(panels)),
                                 squeeze=False)
        for ax, (series, label, colour) in zip(axes[:, 0], panels):
            ax.plot(it[:len(series)], series, "-o", ms=3, color=colour)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(label)
            ax.set_title(label.split(" [")[0] + " Convergence")
            ax.grid(True, alpha=0.3)
            ax.margins(y=0.1)
        fig.tight_layout()
        return fig

    def _page_convergence_from_rows(self, plt, pdf):
        """Convergence plots extracted from gRPC history rows (fallback path)."""
        if not self.history_rows:
            return

        _DISSIP_KEYS = ["DissPower", "dissPower", "Disspower", "dissipation",
                        "objective", "obj"]
        _MEANT_KEYS  = ["meantT", "meanT", "MeanT", "constraint", "g_meanT"]
        _G_OH_KEYS   = ["g_oh", "G_oh"]

        def _extract(rows, keys):
            vals = []
            for row in rows:
                for k in keys:
                    v = row.get(k)
                    if v not in (None, ""):
                        try:
                            vals.append(float(v)); break
                        except (TypeError, ValueError):
                            pass
            return vals

        iters = list(range(len(self.history_rows)))
        objs  = _extract(self.history_rows, _DISSIP_KEYS)
        cstrs = _extract(self.history_rows, _MEANT_KEYS)
        gohs  = _extract(self.history_rows, _G_OH_KEYS)

        _nz = lambda s: s if s and any(v != 0.0 for v in s) else []
        panels = [
            (_nz(objs),  "Objective",                    "tab:blue"),
            (_nz(cstrs), "Mean Temperature Constraint",  "tab:red"),
            (_nz(gohs),  "Overhang Constraint (g_oh)",   "tab:orange"),
        ]
        panels = [(s, l, c) for s, l, c in panels if s]
        if not panels:
            return

        fig, axes = plt.subplots(len(panels), 1,
                                 figsize=(8.27, 3.5 * len(panels)),
                                 squeeze=False)
        fig.suptitle("Convergence History (Server)", fontsize=13, fontweight="bold")
        for ax, (series, label, colour) in zip(axes[:, 0], panels):
            ax.plot(iters[:len(series)], series, "-o", ms=3, color=colour)
            ax.set_xlabel("Iteration")
            ax.set_ylabel(label)
            ax.set_title(f"{label} Convergence")
            ax.grid(True, alpha=0.3)
            ax.margins(y=0.1)
        fig.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _pyvista_screenshot(stl_path: str) -> bytes | None:
        """Render an STL off-screen with PyVista; return PNG bytes or None."""
        try:
            import pyvista as pv
            mesh = pv.read(stl_path)
            pl = pv.Plotter(off_screen=True, window_size=[1200, 800])
            pl.add_mesh(mesh, color="#4A90D9", smooth_shading=True,
                        show_edges=False)
            pl.add_axes()
            pl.set_background("#FFFFFF")
            pl.camera_position = "iso"
            tmp = Path(tempfile.mktemp(suffix=".png"))
            pl.screenshot(str(tmp))
            pl.close()
            data = tmp.read_bytes()
            tmp.unlink(missing_ok=True)
            return data
        except Exception:
            return None

    @staticmethod
    def _dict_to_lines(d: dict, indent: int = 0) -> list[str]:
        out = []
        pad = "  " * indent
        for k, v in d.items():
            if isinstance(v, dict):
                out.append(f"{pad}{k}:")
                out += ReportGenerator._dict_to_lines(v, indent + 1)
            else:
                out.append(f"{pad}{k:.<34} {v}")
        return out
