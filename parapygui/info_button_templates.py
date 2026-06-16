# -*- coding: utf-8 -*-
"""
info_button_templates.py
------------------------
Three patterns for adding info/help icons next to wx widgets.
Copy whichever pattern suits the context.
"""

import wx


# ═══════════════════════════════════════════════════════════════════
# PATTERN 1: Simple tooltip (hover over ⓘ to see explanation)
# Best for: short one-line explanations
# ═══════════════════════════════════════════════════════════════════

def add_info_tip(parent, sizer, tooltip_text):
    """Add a small ⓘ label with a hover tooltip.

    Usage in wxFormBuilder-style code:
        fgSizer.Add(wx.StaticText(panel, label="Reynolds Number:"), ...)
        txt = wx.TextCtrl(panel, ...)
        fgSizer.Add(txt, ...)
        add_info_tip(panel, fgSizer, "Re = ρUDₕ/μ — ratio of inertial to viscous forces")
    """
    info = wx.StaticText(parent, wx.ID_ANY, u" ⓘ")
    info.SetForegroundColour(wx.Colour(100, 150, 220))
    info.SetCursor(wx.Cursor(wx.CURSOR_QUESTION_ARROW))
    info.SetToolTip(tooltip_text)
    sizer.Add(info, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
    return info


# ═══════════════════════════════════════════════════════════════════
# PATTERN 2: Clickable ⓘ button that shows a popup dialog
# Best for: longer explanations with equations or multi-line text
# ═══════════════════════════════════════════════════════════════════

def add_info_button(parent, sizer, title, message):
    """Add a small ⓘ button that opens an info dialog on click.

    Usage:
        add_info_button(panel, fgSizer,
            "Nusselt Number",
            "Nu = 0.023 · Re^0.8 · Pr^0.4 · (1 + 2.5σ)\\n\\n"
            "Represents the ratio of convective to conductive\\n"
            "heat transfer at the surface.\\n\\n"
            "Source: Cheng et al. (2023), DOI: 10.1016/j.enconman.2023.116955")
    """
    btn = wx.Button(parent, wx.ID_ANY, u"ⓘ", size=(24, 24))
    btn.SetForegroundColour(wx.Colour(100, 150, 220))
    font = btn.GetFont()
    font.SetPointSize(10)
    btn.SetFont(font)
    btn.SetToolTip(f"Click for info: {title}")
    btn.Bind(wx.EVT_BUTTON,
             lambda evt: wx.MessageBox(message, title,
                                       wx.OK | wx.ICON_INFORMATION))
    sizer.Add(btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 4)
    return btn


# ═══════════════════════════════════════════════════════════════════
# PATTERN 3: Row helper — label + widget + ⓘ in one call
# Best for: FlexGridSizer layouts with many fields
# ═══════════════════════════════════════════════════════════════════

def add_field_with_info(parent, sizer, label, widget, info_text,
                        popup=False, popup_title=None):
    """Add a complete row: label + widget + ⓘ icon.

    Args:
        parent:     wx parent panel
        sizer:      FlexGridSizer (should have 3 growable columns)
        label:      field label string
        widget:     the wx widget (SpinCtrl, TextCtrl, etc.)
        info_text:  explanation text
        popup:      if True, click opens a dialog; if False, hover tooltip
        popup_title: dialog title (defaults to label)

    Usage:
        fgSizer = wx.FlexGridSizer(0, 3, 5, 10)
        fgSizer.AddGrowableCol(1)

        spin = wx.SpinCtrlDouble(panel, ...)
        add_field_with_info(panel, fgSizer,
            "Solidity:", spin,
            "Volume fraction of solid material in the lattice.\\n"
            "Determined by the iso-level threshold |G| = t.\\n"
            "Higher solidity = thicker walls, more pressure drop.")

        spin2 = wx.SpinCtrlDouble(panel, ...)
        add_field_with_info(panel, fgSizer,
            "Wavenumber (rad/m):", spin2,
            "k = 2π / L_unit\\n\\n"
            "Controls the number of gyroid unit cells.\\n"
            "Higher k = denser lattice = more surface area.",
            popup=True, popup_title="Gyroid Wavenumber")
    """
    sizer.Add(wx.StaticText(parent, wx.ID_ANY, label),
              0, wx.ALIGN_CENTER_VERTICAL)
    sizer.Add(widget, 1, wx.EXPAND)

    if popup:
        title = popup_title or label.rstrip(":").strip()
        add_info_button(parent, sizer, title, info_text)
    else:
        add_info_tip(parent, sizer, info_text)


# ═══════════════════════════════════════════════════════════════════
# EXAMPLE: How to use in your GUIwxformbuilder.py
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = wx.App(False)
    frame = wx.Frame(None, title="Info Button Demo", size=(500, 400))
    panel = wx.Panel(frame)
    sz = wx.BoxSizer(wx.VERTICAL)

    # --- Pattern 1: Tooltip ---
    row1 = wx.BoxSizer(wx.HORIZONTAL)
    row1.Add(wx.StaticText(panel, label="Reynolds Number:"), 0,
             wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    txt1 = wx.TextCtrl(panel, value="1234.5",
                        style=wx.TE_READONLY, size=(100, -1))
    row1.Add(txt1, 0, wx.RIGHT, 4)
    add_info_tip(panel, row1,
                 "Re = ρUDₕ/μ\n"
                 "Ratio of inertial to viscous forces.\n"
                 "Re < 2300 → laminar, Re > 4000 → turbulent")
    sz.Add(row1, 0, wx.ALL, 10)

    # --- Pattern 2: Popup ---
    row2 = wx.BoxSizer(wx.HORIZONTAL)
    row2.Add(wx.StaticText(panel, label="Nusselt Number:"), 0,
             wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 8)
    txt2 = wx.TextCtrl(panel, value="42.7",
                        style=wx.TE_READONLY, size=(100, -1))
    row2.Add(txt2, 0, wx.RIGHT, 4)
    add_info_button(panel, row2,
                    "Nusselt Number",
                    "Nu = 0.023 · Re^0.8 · Pr^0.4 · (1 + 2.5σ)\n\n"
                    "Ratio of convective to conductive heat transfer.\n\n"
                    "Source: Cheng et al. (2023)\n"
                    "DOI: 10.1016/j.enconman.2023.116955")
    sz.Add(row2, 0, wx.ALL, 10)

    # --- Pattern 3: Full row helper ---
    fg = wx.FlexGridSizer(0, 3, 5, 10)
    fg.AddGrowableCol(1)

    spin = wx.SpinCtrlDouble(panel, value="0.3", min=0.05, max=0.95,
                              inc=0.01, size=(100, -1))
    add_field_with_info(panel, fg,
        "Solidity:", spin,
        "Volume fraction of solid material.\n"
        "σ = 0 → all fluid, σ = 1 → all solid.\n"
        "Typical range: 0.2–0.6 for heat exchangers.")

    spin2 = wx.SpinCtrlDouble(panel, value="628.0", min=10, max=5000,
                               inc=10, size=(100, -1))
    add_field_with_info(panel, fg,
        "Wavenumber:", spin2,
        "k = 2π / L_unit\n\n"
        "Controls gyroid cell density.\n"
        "k = 628 rad/m → ~10 cells over 100mm domain.\n\n"
        "⚠ Default 62.8 produces only ~1 cell — too coarse!",
        popup=True, popup_title="Gyroid Wavenumber")

    sz.Add(fg, 0, wx.EXPAND | wx.ALL, 10)

    panel.SetSizer(sz)
    frame.Show()
    app.MainLoop()
