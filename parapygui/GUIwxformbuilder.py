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
        u"Step 1: Geometry & Boundary Conditions",
        u"Step 2: Semi-Empirical Sizing",
        u"Step 3: Baseline Simulation",
        u"Step 4: Optimizer Setup",
        u"Step 5: Optimization Monitor",
        u"Step 6: Results & Post-Processing",
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
        self.m_panelGeom = wx.Panel(self.m_simplebook)
        szG = wx.BoxSizer(wx.VERTICAL)

        # -- domain size (geometry.size_mm) --
        sbDom = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Domain Size (mm)")), wx.HORIZONTAL)
        for lbl, attr, val in [("X:", "m_spinSizeX", 250.0), ("Y:", "m_spinSizeY", 250.0), ("Z:", "m_spinSizeZ", 300.0)]:
            sbDom.Add(wx.StaticText(sbDom.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
            s = wx.SpinCtrlDouble(sbDom.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(90,-1), wx.SP_ARROW_KEYS, 1, 2000, val, 5)
            setattr(self, attr, s); sbDom.Add(s, 0, wx.ALL, 4)
        sbDom.Add(wx.StaticText(sbDom.GetStaticBox(), wx.ID_ANY, _(u"  Flow axis:")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 12)
        self.m_choiceFlowAxis = wx.Choice(sbDom.GetStaticBox(), wx.ID_ANY, choices=["x","y","z"])
        self.m_choiceFlowAxis.SetSelection(2)
        sbDom.Add(self.m_choiceFlowAxis, 0, wx.ALL, 4)
        szG.Add(sbDom, 0, wx.EXPAND|wx.ALL, 5)

        # -- encapsulation --
        sbEnc = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Encapsulation")), wx.HORIZONTAL)
        sbEnc.Add(wx.StaticText(sbEnc.GetStaticBox(), wx.ID_ANY, _(u"Wall thickness (mm):")), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
        self.m_spinEncapWall = wx.SpinCtrlDouble(sbEnc.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(80,-1), wx.SP_ARROW_KEYS, 0.5, 20, 3.0, 0.5)
        sbEnc.Add(self.m_spinEncapWall, 0, wx.ALL, 4)
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
        sbMat = wx.StaticBoxSizer(wx.StaticBox(self.m_panelGeom, wx.ID_ANY, _(u"Material & Thermal")), wx.VERTICAL)
        fgMat = wx.FlexGridSizer(0, 4, 5, 10); fgMat.AddGrowableCol(1); fgMat.AddGrowableCol(3)
        for lbl, attr, lo, hi, val, inc in [
            ("Exterior temp (K):",    "m_spinTexterior",   100, 2000, 270.0, 5),
            ("Initial temp (K):",     "m_spinTinitial",    100, 2000, 270.0, 5),
            ("Kinematic visc (m²/s):", "m_spinNu",         1e-8, 1e-3, 1e-6, 1e-7),
            ("Fluid density (kg/m³):", "m_spinRhoFluid",   0.1, 10000, 1000.0, 10),
        ]:
            fgMat.Add(wx.StaticText(sbMat.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL)
            s = wx.SpinCtrlDouble(sbMat.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(110,-1), wx.SP_ARROW_KEYS, lo, hi, val, inc)
            setattr(self, attr, s); fgMat.Add(s, 0, wx.EXPAND)
        sbMat.Add(fgMat, 0, wx.EXPAND|wx.ALL, 5)
        szG.Add(sbMat, 0, wx.EXPAND|wx.ALL, 5)

        self.m_btnApplyGeom = wx.Button(self.m_panelGeom, wx.ID_ANY, _(u"Apply to model"))
        szG.Add(self.m_btnApplyGeom, 0, wx.ALL, 10)
        self.m_panelGeom.SetSizer(szG); self.m_panelGeom.Layout(); szG.Fit(self.m_panelGeom)
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
        self.m_webviewSE = wx.html2.WebView.New(self.m_panelSE)
        szSE.Add(self.m_webviewSE, 1, wx.EXPAND|wx.ALL, 10)
        self.m_panelSE.SetSizer(szSE); self.m_panelSE.Layout(); szSE.Fit(self.m_panelSE)
        self.m_simplebook.AddPage(self.m_panelSE, u"Sizing", False)

        # =============================================================
        # PAGE 2 — Baseline Simulation
        # =============================================================
        self.m_panelBaseline = wx.Panel(self.m_simplebook)
        szBL = wx.BoxSizer(wx.VERTICAL)
        self.m_btnRunBaseline = wx.Button(self.m_panelBaseline, wx.ID_ANY, _(u"Push Config & Run Baseline"))
        szBL.Add(self.m_btnRunBaseline, 0, wx.ALL, 10)
        self.m_gaugeBaseline = wx.Gauge(self.m_panelBaseline, wx.ID_ANY, 100, wx.DefaultPosition, wx.Size(-1,20))
        szBL.Add(self.m_gaugeBaseline, 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 10)
        self.m_txtBaselineLog = wx.TextCtrl(self.m_panelBaseline, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,140), wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.m_txtBaselineLog.SetFont(mono)
        szBL.Add(self.m_txtBaselineLog, 0, wx.EXPAND|wx.ALL, 10)
        sbBR = wx.StaticBoxSizer(wx.StaticBox(self.m_panelBaseline, wx.ID_ANY, _(u"Results")), wx.HORIZONTAL)
        for lbl, attr in [("Dissipation (W):", "m_txtBaseDissip"), ("Mean Temp (K):", "m_txtBaseMeanT")]:
            sbBR.Add(wx.StaticText(sbBR.GetStaticBox(), wx.ID_ANY, _(lbl)), 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 8)
            t = wx.TextCtrl(sbBR.GetStaticBox(), wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(100,-1), wx.TE_READONLY)
            setattr(self, attr, t); sbBR.Add(t, 0, wx.ALL, 4)
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

        sbCstr = wx.StaticBoxSizer(wx.StaticBox(self.m_panelOpt, wx.ID_ANY, _(u"Constraints & Optimization")), wx.VERTICAL)
        fgC = wx.FlexGridSizer(0, 2, 6, 10); fgC.AddGrowableCol(1)
        for lbl, attr, lo, hi, val, inc in [
            ("meantT_max (K):",        "m_spinMeanTMax",   200, 2000, 340, 5),
            ("dissPower_max (W):",     "m_spinDissPMax",   0, 1e9, 2800000, 10000),
            ("Wall thickness (cells):", "m_spinWallCells",  1, 50, 6, 1),
            ("Unit cell size (cells):", "m_spinUnitCells",  5, 200, 75, 5),
            ("Overhang angle (°):",    "m_spinAmTheta",    0, 90, 45, 1),
            ("Max iterations:",        "m_spinMaxIter",    10, 5000, 100, 10),
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
        self.m_btnStartOpt = wx.Button(self.m_panelMonitor, wx.ID_ANY, _(u"Push Config & Start Optimization"))
        szMon.Add(self.m_btnStartOpt, 0, wx.ALL, 10)
        self.m_webviewConvergence = wx.html2.WebView.New(self.m_panelMonitor)
        szMon.Add(self.m_webviewConvergence, 1, wx.EXPAND|wx.ALL, 5)
        self.m_txtSolverLog = wx.TextCtrl(self.m_panelMonitor, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size(-1,140), wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL)
        self.m_txtSolverLog.SetFont(mono)
        szMon.Add(self.m_txtSolverLog, 0, wx.EXPAND|wx.ALL, 5)
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
        self.m_btnExportSTL = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Export STL"))
        szBtns.Add(self.m_btnExportSTL, 0, wx.ALL, 5)
        self.m_btnPySLM = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Run PySLM"))
        szBtns.Add(self.m_btnPySLM, 0, wx.ALL, 5)
        self.m_btnExportSTEP = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Export STEP"))
        szBtns.Add(self.m_btnExportSTEP, 0, wx.ALL, 5)
        self.m_btnDownloadHist = wx.Button(self.m_panelResults, wx.ID_ANY, _(u"Download History"))
        szBtns.Add(self.m_btnDownloadHist, 0, wx.ALL, 5)
        szRes.Add(szBtns, 0, wx.ALL, 5)
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
        self.m_btnApplyOpt.Bind(wx.EVT_BUTTON, self.onApplyOpt)
        self.m_btnRunBaseline.Bind(wx.EVT_BUTTON, self.onRunBaseline)
        self.m_btnStartOpt.Bind(wx.EVT_BUTTON, self.onStartOpt)
        self.m_btnExportSTL.Bind(wx.EVT_BUTTON, self.onExportSTL)
        self.m_btnPySLM.Bind(wx.EVT_BUTTON, self.onRunPySLM)
        self.m_btnExportSTEP.Bind(wx.EVT_BUTTON, self.onExportSTEP)
        self.m_btnDownloadHist.Bind(wx.EVT_BUTTON, self.onDownloadHistory)

    def __del__( self ): pass
    def onBack( self, event ): event.Skip()
    def onNext( self, event ): event.Skip()
    def onApplyGeom( self, event ): event.Skip()
    def onApplyOpt( self, event ): event.Skip()
    def onRunBaseline( self, event ): event.Skip()
    def onStartOpt( self, event ): event.Skip()
    def onExportSTL( self, event ): event.Skip()
    def onRunPySLM( self, event ): event.Skip()
    def onExportSTEP( self, event ): event.Skip()
    def onDownloadHistory( self, event ): event.Skip()
