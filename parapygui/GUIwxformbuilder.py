# -*- coding: utf-8 -*-
###########################################################################
## Python code generated with wxFormBuilder (version 4.2.1-0-g80c4cb6)
## http://www.wxformbuilder.org/
##
## PLEASE DO *NOT* EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc
import wx.html2
import gettext
_ = gettext.gettext

###########################################################################
## Class WorkflowWizardFrame
###########################################################################

class WorkflowWizardFrame ( wx.Frame ):
    """Wizard popup launched from ParaPy @action. Receives the ParaPy object."""

    NUM_PAGES = 6
    PAGE_TITLES = [
        u"Step 1: Geometry && Boundary Conditions",
        u"Step 2: Semi-Empirical Sizing",
        u"Step 3: Baseline Simulation",
        u"Step 4: Optimizer Setup",
        u"Step 5: Optimization Monitor",
        u"Step 6: Results && Post-Processing",
    ]

    def __init__( self, parent, parapy_obj=None ):
        wx.Frame.__init__( self, parent, id=wx.ID_ANY,
            title=_(u"Heat Exchanger — KBE Workflow"),
            pos=wx.DefaultPosition, size=wx.Size(950, 700),
            style=wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )

        self.parapy_obj = parapy_obj
        self.SetSizeHints( wx.Size(750, 550), wx.DefaultSize )
        mono = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        bSizerMain = wx.BoxSizer( wx.VERTICAL )

        # --- header ---
        self.m_headerLabel = wx.StaticText(self, wx.ID_ANY, _(self.PAGE_TITLES[0]))
        hf = self.m_headerLabel.GetFont(); hf.SetPointSize(13); hf.SetWeight(wx.FONTWEIGHT_BOLD)
        self.m_headerLabel.SetFont(hf)
        bSizerMain.Add(self.m_headerLabel, 0, wx.ALL|wx.EXPAND, 10)
        bSizerMain.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)

        self.m_simplebook = wx.Simplebook(self, wx.ID_ANY)
        bSizerMain.Add(self.m_simplebook, 1, wx.EXPAND|wx.ALL, 5)

        # =============================================================
        # PAGE 0 — Geometry & Boundary Conditions
        # =============================================================
        self.m_panelGeom = wx.ScrolledWindow(self.m_simplebook, style=wx.VSCROLL)
        self.m_panelGeom.SetScrollRate(0, 10)
        szG = wx.BoxSizer(wx.VERTICAL)

        # -- domain size (geometry.size_mm) --
        sbDom = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Domain Size (mm)")), wx.HORIZONTAL)
        for lbl, attr, val in [("X:", "m_spinSizeX", 250.0), ("Y:", "m_spinSizeY", 250.0), ("Z:", "m_spinSizeZ", 300.0)]:
            sbDom.Add(wx.StaticText(sbDom.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
            s = wx.SpinCtrlDouble(sbDom.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(90,-1), wx.SP_ARROW_KEYS, 1, 2000, val, 5)
            setattr(self, attr, s); sbDom.Add(s, 0, wx.ALL, 4)
        szG.Add(sbDom, 0, wx.EXPAND|wx.ALL, 5)

        # -- mesh cells (geometry.cells) --
        sbCells = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Mesh Resolution (cells)")), wx.HORIZONTAL)
        for lbl, attr, val in [("X:", "m_spinCellsX", 75), ("Y:", "m_spinCellsY", 75), ("Z:", "m_spinCellsZ", 90)]:
            sbCells.Add(wx.StaticText(sbCells.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
            s = wx.SpinCtrl(sbCells.GetStaticBox(), wx.ID_ANY, str(val), wx.DefaultPosition, wx.Size(70,-1), wx.SP_ARROW_KEYS, 5, 500, val)
            setattr(self, attr, s); sbCells.Add(s, 0, wx.ALL, 4)
        # total cell count display
        self.m_lblTotalCells = wx.StaticText(sbCells.GetStaticBox(), wx.ID_ANY, _(u"  = 506,250 cells"))
        self.m_lblTotalCells.SetForegroundColour(wx.Colour(120, 120, 120))
        sbCells.Add(self.m_lblTotalCells, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        szG.Add(sbCells, 0, wx.EXPAND|wx.ALL, 5)

        # -- Shape settings --
        sbEnc = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Shape settings")), wx.VERTICAL)
        fgEnc = wx.FlexGridSizer(0, 4, 5, 10); fgEnc.AddGrowableCol(1); fgEnc.AddGrowableCol(3)
        for lbl, attr, lo, hi, val, inc in [
            ("Encapsulation wall (mm):", "m_spinEncapWall",   0.5,  20,   3.0, 0.5),
            ("Gyroid wall (mm):",        "m_spinGyroidWall",  0.01, 10,   0.2, 0.01),
            ("Gyroid unit cell (mm):",   "m_spinGyroidUnit",  0.1,  50,   1.8, 0.1),
            (u"ε smoother (mm):",        "m_spinEpsilon",     0.01, 10,   0.2, 0.01),
            ("Ctrl pt spacing (mm):",    "m_spinSpacing",     0.1,  100,  7.0, 0.1),
            ("RBF resolution (mm):",     "m_spinBakeSpacing", 0.1,  50,   1.4, 0.1),
            ("Wavenumber field max (rad/mm):", "m_spinKboundShape", 0.001, 100, 3.4, 0.1),
        ]:
            fgEnc.Add(wx.StaticText(sbEnc.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbEnc.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(90,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgEnc.Add(s, 0, wx.EXPAND)
        sbEnc.Add(fgEnc, 0, wx.EXPAND|wx.ALL, 5)
        szG.Add(sbEnc, 0, wx.EXPAND|wx.ALL, 5)

        # -- inlet --
        sbIn = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Inlet")), wx.VERTICAL)
        fgIn = wx.FlexGridSizer(0, 4, 5, 10); fgIn.AddGrowableCol(1); fgIn.AddGrowableCol(3)
        for lbl, attr, lo, hi, val, inc in [
            ("Velocity (m/s):",    "m_spinInletVel",  0.01, 100, 2.0, 0.1),
            ("Temperature (K):",   "m_spinInletTemp", 200, 2000, 380.0, 5),
            ("Window origin X (mm):", "m_spinInWinOX", 0, 2000, 10, 1),
            ("Window origin Y (mm):", "m_spinInWinOY", 0, 2000, 10, 1),
            ("Window size X (mm):",   "m_spinInWinSX", 1, 2000, 10, 1),
            ("Window size Y (mm):",   "m_spinInWinSY", 1, 2000, 15, 1),
        ]:
            fgIn.Add(wx.StaticText(sbIn.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbIn.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(110,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgIn.Add(s, 0, wx.EXPAND)
        sbIn.Add(fgIn, 0, wx.EXPAND|wx.ALL, 5)
        szG.Add(sbIn, 0, wx.EXPAND|wx.ALL, 5)

        # -- outlet --
        sbOut = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Outlet")), wx.VERTICAL)
        fgOut = wx.FlexGridSizer(0, 4, 5, 10); fgOut.AddGrowableCol(1); fgOut.AddGrowableCol(3)
        for lbl, attr, lo, hi, val, inc in [
            ("Gauge pressure (Pa):",    "m_spinOutletP",  0, 1e7, 0.0, 100),
            ("Window origin X (mm):",   "m_spinOutWinOX", 0, 2000, 220, 1),
            ("Window origin Y (mm):",   "m_spinOutWinOY", 0, 2000, 220, 1),
            ("Window size X (mm):",     "m_spinOutWinSX", 1, 2000, 10, 1),
            ("Window size Y (mm):",     "m_spinOutWinSY", 1, 2000, 15, 1),
        ]:
            fgOut.Add(wx.StaticText(sbOut.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbOut.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(110,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgOut.Add(s, 0, wx.EXPAND)
        sbOut.Add(fgOut, 0, wx.EXPAND|wx.ALL, 5)
        szG.Add(sbOut, 0, wx.EXPAND|wx.ALL, 5)

        # -- material / thermal --
        sbMat = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Material && Thermal")), wx.VERTICAL)
        fgMat = wx.FlexGridSizer(0, 4, 5, 10); fgMat.AddGrowableCol(1); fgMat.AddGrowableCol(3)
        for lbl, attr, lo, hi, val, inc in [
            ("Exterior temp (K):",          "m_spinTexterior", 100,    2000,   270.0,   5),
            (u"qα / qₖ (shape):",           "m_spinQu",        0.0001, 1.0,    0.005,   0.001),
            (u"Kinematic visc (m²/s):",     "m_spinNu",        1e-8,   1e-3,   1e-6,    1e-7),
            (u"Fluid density (kg/m³):",     "m_spinRhoFluid",  0.1,    10000,  1000.0,  10),
            (u"k_f (W/m·K):",              "m_spinKf",        0.001,  1000,   0.61,    0.01),
            (u"k_s (W/m·K):",              "m_spinKs",        0.001,  10000,  237.0,   1.0),
            (u"cₚ (J/kg·K):",              "m_spinCp",        1,      100000, 4180.0,  10.0),
            (u"ρ_s (g/mm³):",              "m_spinRhoS",      1e-5,   0.1,    0.0027,  0.0001),
            ("Da (Darcy number):",          "m_spinDa",        0,      1e-3,   1e-9,    1e-10),
            (u"h (W/m²·K):",               "m_spinHconv",     0.1,    100000, 1000.0,  10.0),
        ]:
            fgMat.Add(wx.StaticText(sbMat.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbMat.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(110,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgMat.Add(s, 0, wx.EXPAND)
        self.m_spinRhoS.SetDigits(6)
        self.m_spinDa.SetDigits(12)
        sbMat.Add(fgMat, 0, wx.EXPAND|wx.ALL, 5)
        # m_spinTinitial is not shown; it always mirrors m_spinTexterior
        self.m_spinTinitial = wx.SpinCtrlDouble(sbMat.GetStaticBox(), wx.ID_ANY, wx.EmptyString,
            wx.DefaultPosition, wx.Size(110,-1), wx.SP_ARROW_KEYS, 100, 2000, 270.0, 5)
        self.m_spinTinitial.Hide()
        def _sync_tinitial(evt):
            self.m_spinTinitial.SetValue(self.m_spinTexterior.GetValue())
            evt.Skip()
        self.m_spinTexterior.Bind(wx.EVT_SPINCTRLDOUBLE, _sync_tinitial)
        self.m_spinTexterior.Bind(wx.EVT_TEXT, _sync_tinitial)
        szG.Add(sbMat, 0, wx.EXPAND|wx.ALL, 5)

        # -- run settings (applies to all simulations) --
        sbRun = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Run Settings")), wx.VERTICAL)
        # row 1: cores / iterations / opt-method
        szRunRow1 = wx.BoxSizer(wx.HORIZONTAL)
        szRunRow1.Add(wx.StaticText(sbRun.GetStaticBox(), wx.ID_ANY, _(u"Parallel cores:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinCores = wx.SpinCtrl(sbRun.GetStaticBox(), wx.ID_ANY, u"10", wx.DefaultPosition, wx.Size(70,-1), wx.SP_ARROW_KEYS, 1, 64, 10)
        szRunRow1.Add(self.m_spinCores, 0, wx.ALL, 4)
        szRunRow1.Add(wx.StaticText(sbRun.GetStaticBox(), wx.ID_ANY, _(u"  Max iterations:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinMaxIter = wx.SpinCtrlDouble(sbRun.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(90,-1), wx.SP_ARROW_KEYS, 1, 5000, 100, 10)
        szRunRow1.Add(self.m_spinMaxIter, 0, wx.ALL, 4)
        szRunRow1.Add(wx.StaticText(sbRun.GetStaticBox(), wx.ID_ANY, _(u"  Opt. method:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_choiceOptMethod = wx.Choice(sbRun.GetStaticBox(), wx.ID_ANY,
            choices=[u"MMA", u"L-BFGS-B", u"trust-constr", u"pareto"])
        self.m_choiceOptMethod.SetSelection(0)
        szRunRow1.Add(self.m_choiceOptMethod, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 4)
        sbRun.Add(szRunRow1, 0, wx.EXPAND)
        # row 2: mode dropdown + conditional parameter panels
        szRunRow2 = wx.BoxSizer(wx.HORIZONTAL)
        szRunRow2.Add(wx.StaticText(sbRun.GetStaticBox(), wx.ID_ANY, _(u"Mode:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_choiceMode = wx.Choice(sbRun.GetStaticBox(), wx.ID_ANY, choices=[u"pressure", u"heat"])
        self.m_choiceMode.SetSelection(0)
        szRunRow2.Add(self.m_choiceMode, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 4)
        # pressure panel: max average temperature
        self.m_panelMeanT = wx.Panel(sbRun.GetStaticBox(), wx.ID_ANY)
        _szMeanT = wx.BoxSizer(wx.HORIZONTAL)
        _szMeanT.Add(wx.StaticText(self.m_panelMeanT, wx.ID_ANY, _(u"Max avg temp (K):")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinRunMeanTMax = wx.SpinCtrlDouble(self.m_panelMeanT, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(90,-1), wx.SP_ARROW_KEYS, 1, 2000, 303.0, 1.0)
        _szMeanT.Add(self.m_spinRunMeanTMax, 0, wx.ALL, 4)
        self.m_panelMeanT.SetSizer(_szMeanT)
        szRunRow2.Add(self.m_panelMeanT, 0, wx.ALIGN_CENTER_VERTICAL)
        # heat panel: max dissipative power
        self.m_panelDissPMax = wx.Panel(sbRun.GetStaticBox(), wx.ID_ANY)
        _szDissPMax = wx.BoxSizer(wx.HORIZONTAL)
        _szDissPMax.Add(wx.StaticText(self.m_panelDissPMax, wx.ID_ANY, _(u"Max diss. power (W):")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinRunDissPMax = wx.SpinCtrlDouble(self.m_panelDissPMax, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(100,-1), wx.SP_ARROW_KEYS, 0, 1e8, 9800.0, 100.0)
        _szDissPMax.Add(self.m_spinRunDissPMax, 0, wx.ALL, 4)
        self.m_panelDissPMax.SetSizer(_szDissPMax)
        self.m_panelDissPMax.Hide()
        szRunRow2.Add(self.m_panelDissPMax, 0, wx.ALIGN_CENTER_VERTICAL)
        sbRun.Add(szRunRow2, 0, wx.EXPAND|wx.TOP, 4)
        def _on_run_mode(evt):
            sel = self.m_choiceMode.GetCurrentSelection()
            self.m_panelMeanT.Show(sel == 0)
            self.m_panelDissPMax.Show(sel == 1)
            self.m_panelGeom.Layout()
            evt.Skip()
        self.m_choiceMode.Bind(wx.EVT_CHOICE, _on_run_mode)
        # row 3: manufacturability analysis
        szRunRow3 = wx.BoxSizer(wx.HORIZONTAL)
        self.m_radioMfg = wx.RadioBox(sbRun.GetStaticBox(), wx.ID_ANY, _(u"Manufacturability Analysis"),
            choices=[u"On", u"Off"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.m_radioMfg.SetSelection(0)
        szRunRow3.Add(self.m_radioMfg, 0, wx.ALL|wx.ALIGN_TOP, 4)
        # conditional panel shown when mfg is On
        self.m_panelMfgDetails = wx.Panel(sbRun.GetStaticBox(), wx.ID_ANY)
        _szMfg = wx.BoxSizer(wx.VERTICAL)
        _fgMfg = wx.FlexGridSizer(0, 4, 5, 10)
        _fgMfg.AddGrowableCol(1); _fgMfg.AddGrowableCol(3)
        _fgMfg.Add(wx.StaticText(self.m_panelMfgDetails, wx.ID_ANY, _(u"Max overhang angle (°):")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.m_spinRunAmTheta = wx.SpinCtrlDouble(self.m_panelMfgDetails, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(80,-1), wx.SP_ARROW_KEYS, 0, 90, 45.0, 1.0)
        _fgMfg.Add(self.m_spinRunAmTheta, 0, wx.EXPAND)
        _fgMfg.Add(wx.StaticText(self.m_panelMfgDetails, wx.ID_ANY, _(u"Max bridging length (mm):")), 0, wx.ALIGN_CENTER_VERTICAL)
        self.m_spinRunAmLBridge = wx.SpinCtrlDouble(self.m_panelMfgDetails, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(80,-1), wx.SP_ARROW_KEYS, 0.01, 500, 1.5, 0.1)
        _fgMfg.Add(self.m_spinRunAmLBridge, 0, wx.EXPAND)
        _szMfg.Add(_fgMfg, 0, wx.EXPAND|wx.ALL, 4)
        self.m_radioAlignFlow = wx.RadioBox(self.m_panelMfgDetails, wx.ID_ANY, _(u"Align print to flow?"),
            choices=[u"Yes", u"No"], majorDimension=1, style=wx.RA_SPECIFY_ROWS)
        self.m_radioAlignFlow.SetSelection(0)
        _szMfg.Add(self.m_radioAlignFlow, 0, wx.ALL, 4)
        # build direction panel (visible when align=No)
        self.m_panelBuildDir = wx.Panel(self.m_panelMfgDetails, wx.ID_ANY)
        _szBD = wx.BoxSizer(wx.HORIZONTAL)
        _szBD.Add(wx.StaticText(self.m_panelBuildDir, wx.ID_ANY, _(u"Build direction X:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinBuildDirX = wx.SpinCtrlDouble(self.m_panelBuildDir, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(70,-1), wx.SP_ARROW_KEYS, -1000, 1000, 1.0, 0.1)
        _szBD.Add(self.m_spinBuildDirX, 0, wx.ALL, 2)
        _szBD.Add(wx.StaticText(self.m_panelBuildDir, wx.ID_ANY, _(u"Y:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 4)
        self.m_spinBuildDirY = wx.SpinCtrlDouble(self.m_panelBuildDir, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(70,-1), wx.SP_ARROW_KEYS, -1000, 1000, 1.0, 0.1)
        _szBD.Add(self.m_spinBuildDirY, 0, wx.ALL, 2)
        _szBD.Add(wx.StaticText(self.m_panelBuildDir, wx.ID_ANY, _(u"Z:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 4)
        self.m_spinBuildDirZ = wx.SpinCtrlDouble(self.m_panelBuildDir, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(70,-1), wx.SP_ARROW_KEYS, -1000, 1000, 1.0, 0.1)
        _szBD.Add(self.m_spinBuildDirZ, 0, wx.ALL, 2)
        self.m_panelBuildDir.SetSizer(_szBD)
        self.m_panelBuildDir.Hide()
        _szMfg.Add(self.m_panelBuildDir, 0, wx.EXPAND|wx.TOP, 2)
        self.m_panelMfgDetails.SetSizer(_szMfg)
        szRunRow3.Add(self.m_panelMfgDetails, 1, wx.ALIGN_TOP)
        sbRun.Add(szRunRow3, 0, wx.EXPAND|wx.TOP, 4)
        def _on_align_flow(evt):
            self.m_panelBuildDir.Show(self.m_radioAlignFlow.GetSelection() != 0)
            self.m_panelGeom.Layout()
            evt.Skip()
        self.m_radioAlignFlow.Bind(wx.EVT_RADIOBOX, _on_align_flow)
        def _on_mfg(evt):
            self.m_panelMfgDetails.Show(self.m_radioMfg.GetSelection() == 0)
            self.m_panelGeom.Layout()
            evt.Skip()
        self.m_radioMfg.Bind(wx.EVT_RADIOBOX, _on_mfg)
        szG.Add(sbRun, 0, wx.EXPAND|wx.ALL, 5)

        # -- file operations --
        szFileOps = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnLoadJSON = wx.Button(self.m_panelGeom, wx.ID_ANY, _(u"Load Config (JSON)…"))
        self.m_btnLoadJSON.SetToolTip("ⓘ Load a previously saved configuration from the inputs/ folder")
        szFileOps.Add(self.m_btnLoadJSON, 0, wx.ALL, 5)
        self.m_btnSaveJSON = wx.Button(self.m_panelGeom, wx.ID_ANY, _(u"Save Config (JSON)…"))
        self.m_btnSaveJSON.SetToolTip("ⓘ Save current settings to the outputs/ folder for later reuse")
        szFileOps.Add(self.m_btnSaveJSON, 0, wx.ALL, 5)
        self.m_btnApplyGeom = wx.Button(self.m_panelGeom, wx.ID_ANY, _(u"Apply to model"))
        szFileOps.Add(self.m_btnApplyGeom, 0, wx.ALL, 5)
        szG.Add(szFileOps, 0, wx.ALL, 5)
        self.m_panelGeom.SetSizer(szG); self.m_panelGeom.Layout()
        self.m_simplebook.AddPage(self.m_panelGeom, u"Geometry", True)

        # =============================================================
        # PAGE 1 — Semi-Empirical Sizing
        # =============================================================
        self.m_panelSE = wx.Panel(self.m_simplebook)
        szSE = wx.BoxSizer(wx.VERTICAL)
        sbSE = wx.StaticBoxSizer(wx.StaticBox(self.m_panelSE, wx.ID_ANY, _(u"Computed Properties")), wx.VERTICAL)
        fgSE = wx.FlexGridSizer(0, 2, 6, 10); fgSE.AddGrowableCol(1)
        for lbl, attr in [("Reynolds Number:","m_txtReynolds"),("Solidity:","m_txtSolidity"),
                          ("Nusselt Number:","m_txtNusselt"),("Friction Factor:","m_txtFriction"),
                          ("Estimated Pressure Drop (Pa):","m_txtPressureDrop"),
                          ("Hydraulic Diameter (m):","m_txtDh")]:
            fgSE.Add(wx.StaticText(sbSE.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            t = wx.TextCtrl(sbSE.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, wx.TE_READONLY)
            setattr(self, attr, t); fgSE.Add(t, 1, wx.EXPAND)
        sbSE.Add(fgSE, 0, wx.EXPAND|wx.ALL, 5)
        szSE.Add(sbSE, 0, wx.EXPAND|wx.ALL, 10)
        # Info note
        info = wx.StaticText(self.m_panelSE, wx.ID_ANY,
            _(u"ⓘ These values are computed from the semi-empirical correlations "
              u"(Cheng et al. 2023, DOI: 10.1016/j.enconman.2023.116955). "
              u"Replace placeholder Dittus-Boelter fits with actual gyroid TPMS data for production use."))
        info.Wrap(600)
        info.SetForegroundColour(wx.Colour(120, 120, 120))
        szSE.Add(info, 0, wx.ALL, 10)
        self.m_panelSE.SetSizer(szSE); self.m_panelSE.Layout(); szSE.Fit(self.m_panelSE)
        self.m_simplebook.AddPage(self.m_panelSE, u"Sizing", False)

        # =============================================================
        # PAGE 2 — Baseline Simulation
        # =============================================================
        self.m_panelBaseline = wx.Panel(self.m_simplebook)
        szBL = wx.BoxSizer(wx.VERTICAL)
        self.m_btnRunBaseline = wx.Button(self.m_panelBaseline, wx.ID_ANY, _(u"Run Baseline Simulation"))
        self.m_btnRunBaseline.SetToolTip("ⓘ Runs a single optimizer iteration with the uniform gyroid (dk=0). Establishes reference dissipation and temperature.")
        szBL.Add(self.m_btnRunBaseline, 0, wx.ALL, 10)
        self.m_gaugeBaseline = wx.Gauge(self.m_panelBaseline, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size(-1,20))
        szBL.Add(self.m_gaugeBaseline, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
        self.m_txtBaselineLog = wx.TextCtrl(self.m_panelBaseline, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,140), wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.m_txtBaselineLog.SetFont(mono)
        szBL.Add(self.m_txtBaselineLog, 1, wx.EXPAND|wx.ALL, 10)
        sbBR = wx.StaticBoxSizer(wx.StaticBox(self.m_panelBaseline, wx.ID_ANY, _(u"Results")), wx.HORIZONTAL)
        for lbl, attr in [("Dissipation (W):", "m_txtBaseDissip"), ("Mean Temp (K):", "m_txtBaseMeanT")]:
            sbBR.Add(wx.StaticText(sbBR.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
            t = wx.StaticText(sbBR.GetStaticBox(), wx.ID_ANY, u"—", wx.DefaultPosition, wx.Size(100,-1))
            t.SetForegroundColour(wx.Colour(0, 100, 180))
            setattr(self, attr, t); sbBR.Add(t, 0, wx.ALL|wx.ALIGN_CENTER_VERTICAL, 4)
        szBL.Add(sbBR, 0, wx.EXPAND|wx.ALL, 10)
        self.m_webviewBaseline = wx.html2.WebView.New(self.m_panelBaseline)
        szBL.Add(self.m_webviewBaseline, 1, wx.EXPAND|wx.ALL, 10)
        self.m_panelBaseline.SetSizer(szBL); self.m_panelBaseline.Layout(); szBL.Fit(self.m_panelBaseline)
        self.m_simplebook.AddPage(self.m_panelBaseline, u"Baseline", False)

        # =============================================================
        # PAGE 3 — Optimizer Setup
        # =============================================================
        self.m_panelOpt = wx.Panel(self.m_simplebook)
        szOpt = wx.BoxSizer(wx.VERTICAL)

        self.m_radioMode = wx.RadioBox(self.m_panelOpt, wx.ID_ANY,
            _(u"optimization.mode"), wx.DefaultPosition, wx.DefaultSize,
            [_(u"pressure  (min dissipation, temp ≤ meantT_max)"),
             _(u"heat  (min mean temp, dissipation ≤ dissPower_max)")],
            1, wx.RA_SPECIFY_COLS)
        self.m_radioMode.SetSelection(0)
        szOpt.Add(self.m_radioMode, 0, wx.EXPAND|wx.ALL, 10)

        sbCstr = wx.StaticBoxSizer(wx.StaticBox(self.m_panelOpt, wx.ID_ANY, _(u"Constraints && Optimization")), wx.VERTICAL)
        fgC = wx.FlexGridSizer(0, 2, 6, 10); fgC.AddGrowableCol(1)
        for lbl, attr, lo, hi, val, inc in [
            ("meantT_max (K):",        "m_spinMeanTMax",   200, 2000, 340, 5),
            ("dissPower_max (W):",     "m_spinDissPMax",   0, 1e9, 2800000, 10000),
            ("Wall thickness (cells):", "m_spinWallCells",  1, 50, 6, 1),
            ("Unit cell size (cells):", "m_spinUnitCells",  5, 200, 75, 5),
            ("Overhang angle (°):",    "m_spinAmTheta",    0, 90, 45, 1),
            ("kbound:",                "m_spinKbound",     0.001, 1.0, 0.08, 0.01),
        ]:
            fgC.Add(wx.StaticText(sbCstr.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbCstr.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(130,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgC.Add(s, 0, wx.EXPAND)
        sbCstr.Add(fgC, 0, wx.EXPAND|wx.ALL, 5)

        self.m_chkNoOverhang = wx.CheckBox(sbCstr.GetStaticBox(), wx.ID_ANY, _(u"Enable overhang constraint (no_overhang=true)"))
        sbCstr.Add(self.m_chkNoOverhang, 0, wx.ALL, 5)
        szOpt.Add(sbCstr, 0, wx.EXPAND|wx.ALL, 10)

        self.m_btnApplyOpt = wx.Button(self.m_panelOpt, wx.ID_ANY, _(u"Apply settings to model"))
        szOpt.Add(self.m_btnApplyOpt, 0, wx.ALL, 10)
        self.m_panelOpt.SetSizer(szOpt); self.m_panelOpt.Layout(); szOpt.Fit(self.m_panelOpt)
        self.m_simplebook.AddPage(self.m_panelOpt, u"Optimizer", False)

        # =============================================================
        # PAGE 4 — Optimization Monitor
        # =============================================================
        self.m_panelMonitor = wx.Panel(self.m_simplebook)
        szMon = wx.BoxSizer(wx.VERTICAL)
        self.m_btnStartOpt = wx.Button(self.m_panelMonitor, wx.ID_ANY, _(u"Start Optimisation"))
        self.m_btnStartOpt.SetToolTip("ⓘ Pushes config to the Docker server and starts the MMA adjoint topology optimiser. Monitor convergence in real-time below.")
        szMon.Add(self.m_btnStartOpt, 0, wx.ALL, 10)
        self.m_webviewConvergence = wx.html2.WebView.New(self.m_panelMonitor)
        szMon.Add(self.m_webviewConvergence, 1, wx.EXPAND|wx.ALL, 5)
        self.m_txtSolverLog = wx.TextCtrl(self.m_panelMonitor, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,140), wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.m_txtSolverLog.SetFont(mono)
        szMon.Add(self.m_txtSolverLog, 1, wx.EXPAND|wx.ALL, 5)
        self.m_panelMonitor.SetSizer(szMon); self.m_panelMonitor.Layout(); szMon.Fit(self.m_panelMonitor)
        self.m_simplebook.AddPage(self.m_panelMonitor, u"Monitor", False)

        # =============================================================
        # PAGE 5 — Results & Post-Processing
        # =============================================================
        self.m_panelResults = wx.Panel(self.m_simplebook)
        szRes = wx.BoxSizer(wx.VERTICAL)
        sbFin = wx.StaticBoxSizer(wx.StaticBox(self.m_panelResults, wx.ID_ANY, _(u"Final Results")), wx.VERTICAL)
        fgF = wx.FlexGridSizer(0, 4, 6, 10); fgF.AddGrowableCol(1); fgF.AddGrowableCol(3)
        for lbl, attr in [("Dissipation (W):","m_txtOptDissip"),("Mean Temp (K):","m_txtOptMeanT"),
                          ("Iterations:","m_txtIterCount"),("Converged:","m_txtConverged")]:
            fgF.Add(wx.StaticText(sbFin.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            t = wx.TextCtrl(sbFin.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(120,-1), wx.TE_READONLY)
            setattr(self, attr, t); fgF.Add(t, 0, wx.EXPAND)
        sbFin.Add(fgF, 0, wx.EXPAND|wx.ALL, 5)
        szRes.Add(sbFin, 0, wx.EXPAND|wx.ALL, 10)
        szBtns = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnExportSTL = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Export && Download STL"))
        szBtns.Add(self.m_btnExportSTL, 0, wx.ALL, 5)
        self.m_btnViewSTL = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"View STL (PyVista)"))
        self.m_btnViewSTL.Enable(False)
        szBtns.Add(self.m_btnViewSTL, 0, wx.ALL, 5)
        self.m_btnQuadMesh = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Quad Mesh Export (STEP)…"))
        szBtns.Add(self.m_btnQuadMesh, 0, wx.ALL, 5)
        self.m_btnPySLM = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Run PySLM"))
        szBtns.Add(self.m_btnPySLM, 0, wx.ALL, 5)
        self.m_btnDownloadHist = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Download History"))
        szBtns.Add(self.m_btnDownloadHist, 0, wx.ALL, 5)
        szRes.Add(szBtns, 0, wx.ALL, 5)

        # utility row
        szUtil = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnServerStatus = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Server Status"))
        szUtil.Add(self.m_btnServerStatus, 0, wx.ALL, 5)
        self.m_btnListFiles = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"List Server Files"))
        szUtil.Add(self.m_btnListFiles, 0, wx.ALL, 5)
        self.m_btnDownloadApp = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Download Full Case"))
        szUtil.Add(self.m_btnDownloadApp, 0, wx.ALL, 5)
        szRes.Add(szUtil, 0, wx.ALL, 5)
        self.m_webviewResults = wx.html2.WebView.New(self.m_panelResults)
        szRes.Add(self.m_webviewResults, 1, wx.EXPAND|wx.ALL, 10)
        self.m_panelResults.SetSizer(szRes); self.m_panelResults.Layout(); szRes.Fit(self.m_panelResults)
        self.m_simplebook.AddPage(self.m_panelResults, u"Results", False)

        # =============================================================
        # Footer
        # =============================================================
        bSizerMain.Add(wx.StaticLine(self), 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
        szFoot = wx.BoxSizer(wx.HORIZONTAL)
        self.m_statusLabel = wx.StaticText(self, wx.ID_ANY, _(u"Ready"))
        self.m_statusLabel.SetForegroundColour(wx.Colour(120,120,120))
        szFoot.Add(self.m_statusLabel, 1, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 10)
        self.m_btnBack = wx.Button(self, wx.ID_ANY, _(u"◀ Back"), wx.DefaultPosition, wx.Size(90,-1))
        self.m_btnBack.Enable(False)
        szFoot.Add(self.m_btnBack, 0, wx.ALL, 5)
        self.m_btnNext = wx.Button(self, wx.ID_ANY, _(u"Next ▶"), wx.DefaultPosition, wx.Size(90,-1))
        szFoot.Add(self.m_btnNext, 0, wx.ALL, 5)
        bSizerMain.Add(szFoot, 0, wx.EXPAND|wx.ALL, 5)

        self.SetSizer(bSizerMain); self.Layout(); self.Centre(wx.BOTH)

        # ---- Connect Events ----
        self.m_btnBack.Bind(wx.EVT_BUTTON, self.onBack)
        self.m_btnNext.Bind(wx.EVT_BUTTON, self.onNext)
        self.m_btnApplyGeom.Bind(wx.EVT_BUTTON, self.onApplyGeom)
        self.m_btnLoadJSON.Bind(wx.EVT_BUTTON, self.onLoadJSON)
        self.m_btnSaveJSON.Bind(wx.EVT_BUTTON, self.onSaveJSON)
        self.m_spinCellsX.Bind(wx.EVT_SPINCTRL, self.onCellsChanged)
        self.m_spinCellsY.Bind(wx.EVT_SPINCTRL, self.onCellsChanged)
        self.m_spinCellsZ.Bind(wx.EVT_SPINCTRL, self.onCellsChanged)
        self.m_btnApplyOpt.Bind(wx.EVT_BUTTON, self.onApplyOpt)
        self.m_btnRunBaseline.Bind(wx.EVT_BUTTON, self.onRunBaseline)
        self.m_btnStartOpt.Bind(wx.EVT_BUTTON, self.onStartOpt)
        self.m_btnExportSTL.Bind(wx.EVT_BUTTON, self.onExportSTL)
        self.m_btnViewSTL.Bind(wx.EVT_BUTTON, self.onViewSTL)
        self.m_btnQuadMesh.Bind(wx.EVT_BUTTON, self.onQuadMeshExport)
        self.m_btnPySLM.Bind(wx.EVT_BUTTON, self.onRunPySLM)
        self.m_btnDownloadHist.Bind(wx.EVT_BUTTON, self.onDownloadHistory)
        self.m_btnServerStatus.Bind(wx.EVT_BUTTON, self.onServerStatus)
        self.m_btnListFiles.Bind(wx.EVT_BUTTON, self.onListFiles)
        self.m_btnDownloadApp.Bind(wx.EVT_BUTTON, self.onDownloadApp)

    def __del__( self ): pass
    def onBack( self, event ): event.Skip()
    def onNext( self, event ): event.Skip()
    def onApplyGeom( self, event ): event.Skip()
    def onLoadJSON( self, event ): event.Skip()
    def onSaveJSON( self, event ): event.Skip()
    def onCellsChanged( self, event ): event.Skip()
    def onApplyOpt( self, event ): event.Skip()
    def onRunBaseline( self, event ): event.Skip()
    def onStartOpt( self, event ): event.Skip()
    def onExportSTL( self, event ): event.Skip()
    def onViewSTL( self, event ): event.Skip()
    def onQuadMeshExport( self, event ): event.Skip()
    def onRunPySLM( self, event ): event.Skip()
    def onDownloadHistory( self, event ): event.Skip()
    def onServerStatus( self, event ): event.Skip()
    def onListFiles( self, event ): event.Skip()
    def onDownloadApp( self, event ): event.Skip()

###########################################################################
## Class QuadMeshExportDialog
###########################################################################

class QuadMeshExportDialog ( wx.Dialog ):
    """Popup dialog for CGAL quad-mesh → NURBS STEP pipeline."""

    def __init__( self, parent ):
        wx.Dialog.__init__( self, parent, id=wx.ID_ANY,
            title=_(u"Quad Mesh → NURBS → STEP Export"),
            size=wx.Size(950, 750),
            style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER )

        self.SetSizeHints(wx.Size(700, 550))
        mono = wx.Font(9, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

        # Split: left = scrollable params, right = log + preview
        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)

        # ── LEFT: scrollable parameters ──
        scrolled = wx.ScrolledWindow(splitter, style=wx.VSCROLL)
        scrolled.SetScrollRate(0, 10)
        szLeft = wx.BoxSizer(wx.VERTICAL)

        # -- CGAL parameters --
        sbCGAL = wx.StaticBoxSizer(wx.StaticBox(scrolled, wx.ID_ANY, _(u"CGAL Meshing Parameters")), wx.VERTICAL)
        fgP = wx.FlexGridSizer(0, 2, 6, 12); fgP.AddGrowableCol(1)
        for lbl, attr, lo, hi, val, inc, tip in [
            ("Angular criterion (°):",    "m_spinAngular",    1, 90, 30, 1,
             "Minimum facet angle for CGAL surface meshing"),
            ("Radius criterion (mm):",    "m_spinRadius",     0.1, 50, 1.0, 0.1,
             "Maximum surface approximation radius"),
            ("Distance criterion (mm):",  "m_spinDistance",   0.1, 50, 3.5, 0.1,
             "Maximum distance from surface"),
            ("Target faces:",             "m_spinTargetFaces", 1000, 500000, 50000, 5000,
             "Target number of triangular faces (quad count will differ)"),
            ("Crease angle (°):",         "m_spinCrease",     1, 90, 25, 1,
             "Angle threshold for crease detection"),
            ("Smoothing iterations:",     "m_spinSmooth",     0, 50, 0, 1,
             "Instant Meshes smoothing passes (-S flag); 0 avoids a known crash on complex meshes"),
            ("Taubin iterations:",        "m_spinTaubin",     0, 100, 10, 1,
             "Taubin smoothing iterations (shape preserving)"),
            ("Weld tolerance (mm):",      "m_spinWeldTol",    0.01, 10, 0.5, 0.05,
             "Vertex welding tolerance"),
        ]:
            fgP.Add(wx.StaticText(sbCGAL.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbCGAL.GetStaticBox(), wx.ID_ANY, wx.EmptyString,
                wx.DefaultPosition, wx.Size(120,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            s.SetToolTip(tip)
            setattr(self, attr, s)
            fgP.Add(s, 0, wx.EXPAND)
        sbCGAL.Add(fgP, 0, wx.EXPAND|wx.ALL, 5)

        self.m_chkNoBoundary = wx.CheckBox(sbCGAL.GetStaticBox(), wx.ID_ANY, _(u"Disable boundary surfaces (--no-boundary)"))
        sbCGAL.Add(self.m_chkNoBoundary, 0, wx.ALL, 5)

        szLeft.Add(sbCGAL, 0, wx.EXPAND|wx.ALL, 10)

        # -- NURBS / STEP parameters (quad_to_nurbs.py) --
        sbNURBS = wx.StaticBoxSizer(wx.StaticBox(scrolled, wx.ID_ANY, _(u"NURBS → STEP (quad_to_nurbs.py)")), wx.VERTICAL)
        fgN = wx.FlexGridSizer(0, 2, 6, 12); fgN.AddGrowableCol(1)
        for lbl, attr, lo, hi, val, inc, tip in [
            ("Catmull-Clark subdivisions:",  "m_spinSubd",    0, 5, 1, 1,
             "CC subdivision levels (higher = smoother, slower)"),
            ("B-spline degree min:",         "m_spinDegMin",  1, 8, 3, 1,
             "Minimum B-spline surface degree"),
            ("B-spline degree max:",         "m_spinDegMax",  1, 12, 8, 1,
             "Maximum B-spline surface degree"),
            ("Fitting tolerance (mm):",      "m_spinFitTol",  0.0001, 1.0, 0.001, 0.0005,
             "B-spline fitting tolerance"),
            ("Sewing tolerance (mm):",       "m_spinSewTol",  0.001, 1.0, 0.05, 0.005,
             "OCC sewing tolerance for closing seams"),
            ("Max faces (0=all):",           "m_spinMaxFaces", 0, 500000, 0, 1000,
             "Process only first N quads (0 = all); useful for testing"),
        ]:
            fgN.Add(wx.StaticText(sbNURBS.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbNURBS.GetStaticBox(), wx.ID_ANY, wx.EmptyString,
                wx.DefaultPosition, wx.Size(120,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            s.SetToolTip(tip)
            setattr(self, attr, s)
            fgN.Add(s, 0, wx.EXPAND)
        sbNURBS.Add(fgN, 0, wx.EXPAND|wx.ALL, 5)

        # Which sheet to convert
        szSheet = wx.BoxSizer(wx.HORIZONTAL)
        szSheet.Add(wx.StaticText(sbNURBS.GetStaticBox(), wx.ID_ANY, _(u"Sheet:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 8)
        self.m_radioSheet = wx.RadioBox(sbNURBS.GetStaticBox(), wx.ID_ANY, wx.EmptyString,
            wx.DefaultPosition, wx.DefaultSize, ["plus", "minus", "both"], 3, wx.RA_SPECIFY_COLS)
        self.m_radioSheet.SetSelection(0)
        szSheet.Add(self.m_radioSheet, 0)
        sbNURBS.Add(szSheet, 0, wx.ALL, 5)

        szLeft.Add(sbNURBS, 0, wx.EXPAND|wx.ALL, 10)

        # -- Output filename --
        sbOut = wx.StaticBoxSizer(wx.StaticBox(scrolled, wx.ID_ANY, _(u"Output")), wx.HORIZONTAL)
        sbOut.Add(wx.StaticText(sbOut.GetStaticBox(), wx.ID_ANY, _(u"Filename:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        self.m_txtOutFile = wx.TextCtrl(sbOut.GetStaticBox(), wx.ID_ANY, u"gyroid_implicit_qf.obj")
        sbOut.Add(self.m_txtOutFile, 1, wx.EXPAND|wx.ALL, 5)
        szLeft.Add(sbOut, 0, wx.EXPAND|wx.ALL, 10)

        scrolled.SetSizer(szLeft)

        # ── RIGHT: log + preview ──
        rightPanel = wx.Panel(splitter)
        szRight = wx.BoxSizer(wx.VERTICAL)

        # -- Action buttons --
        szActions = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnRunQuadMesh = wx.Button(rightPanel, wx.ID_ANY, _(u"1. Generate Quad Mesh"))
        szActions.Add(self.m_btnRunQuadMesh, 0, wx.ALL, 5)
        self.m_btnConvertNurbs = wx.Button(rightPanel, wx.ID_ANY, _(u"2. Convert to STEP"))
        self.m_btnConvertNurbs.Enable(False)
        szActions.Add(self.m_btnConvertNurbs, 0, wx.ALL, 5)
        self.m_btnStopQuadMesh = wx.Button(rightPanel, wx.ID_ANY, _(u"Stop"))
        self.m_btnStopQuadMesh.Enable(False)
        szActions.Add(self.m_btnStopQuadMesh, 0, wx.ALL, 5)
        szRight.Add(szActions, 0, wx.ALL, 5)

        szActions2 = wx.BoxSizer(wx.HORIZONTAL)
        self.m_btnDownloadOBJ = wx.Button(rightPanel, wx.ID_ANY, _(u"Download OBJ"))
        self.m_btnDownloadOBJ.Enable(False)
        szActions2.Add(self.m_btnDownloadOBJ, 0, wx.ALL, 5)
        self.m_btnDownloadSTEP = wx.Button(rightPanel, wx.ID_ANY, _(u"Download STEP"))
        self.m_btnDownloadSTEP.Enable(False)
        szActions2.Add(self.m_btnDownloadSTEP, 0, wx.ALL, 5)
        self.m_btnViewPyVista = wx.Button(rightPanel, wx.ID_ANY, _(u"View in PyVista"))
        self.m_btnViewPyVista.Enable(False)
        szActions2.Add(self.m_btnViewPyVista, 0, wx.ALL, 5)
        szRight.Add(szActions2, 0, wx.ALL, 5)

        # -- Log --
        self.m_txtQMLog = wx.TextCtrl(rightPanel, wx.ID_ANY, wx.EmptyString,
            wx.DefaultPosition, wx.Size(-1, 200),
            wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.m_txtQMLog.SetFont(mono)
        szRight.Add(self.m_txtQMLog, 1, wx.EXPAND|wx.ALL, 5)

        # -- Status --
        self.m_statusQM = wx.StaticText(rightPanel, wx.ID_ANY, _(u"Ready"))
        self.m_statusQM.SetForegroundColour(wx.Colour(120,120,120))
        szRight.Add(self.m_statusQM, 0, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)

        # -- Preview --
        self.m_webviewQMPreview = wx.html2.WebView.New(rightPanel)
        szRight.Add(self.m_webviewQMPreview, 1, wx.EXPAND|wx.ALL, 5)

        rightPanel.SetSizer(szRight)

        # ── Assemble splitter ──
        splitter.SplitVertically(scrolled, rightPanel, 380)
        splitter.SetMinimumPaneSize(250)

        szMain = wx.BoxSizer(wx.VERTICAL)
        szMain.Add(splitter, 1, wx.EXPAND)
        self.SetSizer(szMain); self.Layout(); self.Centre(wx.BOTH)

        # ---- Connect Events (virtual) ----
        self.m_btnRunQuadMesh.Bind(wx.EVT_BUTTON, self.onRunQuadMesh)
        self.m_btnConvertNurbs.Bind(wx.EVT_BUTTON, self.onConvertNurbs)
        self.m_btnStopQuadMesh.Bind(wx.EVT_BUTTON, self.onStopQuadMesh)
        self.m_btnViewPyVista.Bind(wx.EVT_BUTTON, self.onViewPyVista)
        self.m_btnDownloadOBJ.Bind(wx.EVT_BUTTON, self.onDownloadOBJ)
        self.m_btnDownloadSTEP.Bind(wx.EVT_BUTTON, self.onDownloadSTEP)

    def get_extra_args(self):
        """Build the CLI args list for the quad-mesh gRPC call."""
        args = []
        args += ["--out", self.m_txtOutFile.GetValue()]
        args += ["--angular", str(self.m_spinAngular.GetValue())]
        args += ["--radius", str(self.m_spinRadius.GetValue())]
        args += ["--distance", str(self.m_spinDistance.GetValue())]
        args += ["--target-faces", str(int(self.m_spinTargetFaces.GetValue()))]
        args += ["--crease", str(self.m_spinCrease.GetValue())]
        args += ["--smooth", str(int(self.m_spinSmooth.GetValue()))]
        args += ["--taubin-iter", str(int(self.m_spinTaubin.GetValue()))]
        args += ["--weld-tol", str(self.m_spinWeldTol.GetValue())]
        if self.m_chkNoBoundary.GetValue():
            args.append("--no-boundary")
        return args

    def get_nurbs_args(self):
        """Build the CLI args list for the quad_to_nurbs.py gRPC call."""
        args = []
        args += ["--subd", str(int(self.m_spinSubd.GetValue()))]
        args += ["--deg-min", str(int(self.m_spinDegMin.GetValue()))]
        args += ["--deg-max", str(int(self.m_spinDegMax.GetValue()))]
        args += ["--tol", str(self.m_spinFitTol.GetValue())]
        args += ["--sew-tol", str(self.m_spinSewTol.GetValue())]
        mf = int(self.m_spinMaxFaces.GetValue())
        if mf > 0:
            args += ["--max-faces", str(mf)]
        return args

    def get_sheet_selection(self):
        """Return 'plus', 'minus', or ['plus','minus'] for both."""
        sel = self.m_radioSheet.GetSelection()
        if sel == 0: return ["plus"]
        if sel == 1: return ["minus"]
        return ["plus", "minus"]

    def __del__( self ): pass
    def onRunQuadMesh( self, event ): event.Skip()
    def onConvertNurbs( self, event ): event.Skip()
    def onStopQuadMesh( self, event ): event.Skip()
    def onViewPyVista( self, event ): event.Skip()
    def onDownloadOBJ( self, event ): event.Skip()
    def onDownloadSTEP( self, event ): event.Skip()
