"""
parapygui — Bio-Inspired Heat Exchanger KBE Application
========================================================
TU Delft AE4204 — Team 16 (Desai & Huirne)

This package contains the ParaPy-based KBE application for the
bio-inspired heat exchanger design tool.  The topology optimiser
(MTO / OpenFOAM) lives in a Docker container and is accessed via
gRPC through ``client.py`` in the repo root.
"""

from .fluid import FluidElement
from .lattice import LatticeElement, TPMSFrequencyField, LatticeFormulation
from .encapsulation import InletOutletSpec, Encapsulation
from .environment import HeatExchangerEnvironment
from .objectives import ManufacturingConstraintSet, Objectives
from .solidity import SemiEmpirical
from .simulation import SimulationConnector
from .geometry_export import GeometryExportService
from .loader import Loader
from .gyroid import GyroidMesh
from .manufacturability import ManufacturabilityAnalysis
from .pyslm_analysis import PySLMAnalysis
from .optimization_history import OptimizationHistory
from .reporting import ReportGenerator
from .heat_exchanger import HeatExchanger
