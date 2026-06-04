"""
FloodStack engine adapters.

Each engine wraps an external tool and translates its outputs
into the common DepthGrid data model.

Available engines:
  - TRITONEngine     — ORNL GPU-accelerated 2D hydraulics
  - RASAgentEngine   — HEC-RAS via RAS Agent (regulatory)
  - SPHEREEngine     — HAZUS consequence estimation via SPHERE
"""

from .base import HydraulicEngine, ConsequenceEngine
from .triton import TRITONEngine
from .hec_ras import RASAgentEngine
from .sphere import InlandConsequencesEngine, SPHEREEngine  # SPHEREEngine is alias

__all__ = [
    "HydraulicEngine",
    "ConsequenceEngine",
    "TRITONEngine",
    "RASAgentEngine",
    "InlandConsequencesEngine",
    "SPHEREEngine",  # alias
]
