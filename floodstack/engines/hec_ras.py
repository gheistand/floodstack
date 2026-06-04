"""
RASAgentEngine — adapter for HEC-RAS via RAS Agent.

RAS Agent: https://github.com/Reep-Works/ras-agent
HEC-RAS: US Army Corps of Engineers hydraulic model (FEMA-accepted)

Use for:
  - FEMA FIRM revisions (LOMA, LOMR, CLOMR)
  - NFIP regulatory deliverables
  - Any work requiring FEMA standard of care
  - High-fidelity single runs where regulatory acceptance is required

NOT for:
  - Large ensemble runs (too slow without GPU acceleration)
  - First-pass portfolio screening (use TRITONEngine for triage)
"""

from .base import HydraulicEngine
from ..io.depth_grid import DepthGrid, DepthGridSet


class RASAgentEngine(HydraulicEngine):
    """
    Adapter for HEC-RAS via RAS Agent.

    Args:
        ras_project:  Path to HEC-RAS .prj file (for existing projects)
        ras_exe:      Path to HEC-RAS executable. Defaults to auto-detect.
        agent_config: Path to RAS Agent config. Defaults to ~/.ras-agent/config.yml
    """

    def __init__(
        self,
        ras_project: str = None,
        ras_exe: str = None,
        agent_config: str = None,
    ):
        self.ras_project = ras_project
        self.ras_exe = ras_exe
        self.agent_config = agent_config

    def run(self, terrain: str, flows, **kwargs) -> DepthGridSet:
        """
        Run HEC-RAS via RAS Agent.

        TODO: implement adapter
        - Invoke RAS Agent with terrain + flow inputs
        - Parse HEC-RAS HDF5 output (2D mesh results)
        - Resample unstructured mesh → structured DepthGrid raster
        - Return as DepthGridSet (one per return period)
        """
        raise NotImplementedError(
            "RASAgentEngine adapter not yet implemented. "
            "See docs/architecture.md for the integration spec."
        )

    @property
    def supports_ensemble(self) -> bool:
        return False  # Not efficient for large ensembles; use TRITON

    @property
    def regulatory_grade(self) -> bool:
        return True  # FEMA-accepted; only engine with this flag

    @property
    def compute_backend(self) -> str:
        return "cpu"
