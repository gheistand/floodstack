"""
TRITONEngine — adapter for ORNL's GPU-accelerated 2D hydraulic model.

TRITON: Two-dimensional Runoff Inundation Toolkit for Operational Needs
Site: https://triton.ornl.gov
Docs: https://triton-ornl.readthedocs.io

Use for:
  - Ensemble/climate scenario runs (GPU acceleration = ~100x CPU speedup)
  - Portfolio triage (fast screening before regulatory HEC-RAS runs)
  - Pluvial (gridded runoff hydrograph input supported)
  - Large-scale inundation where regulatory acceptance is not required

NOT for:
  - FEMA FIRM revisions or NFIP regulatory deliverables (use RASAgentEngine)
"""

from .base import HydraulicEngine
from ..io.depth_grid import DepthGrid, DepthGridSet


class TRITONEngine(HydraulicEngine):
    """
    Adapter for TRITON v2 (ORNL).

    Args:
        gpu:        Use GPU acceleration (requires CUDA). Default True.
        n_gpus:     Number of GPUs for multi-GPU runs. Default 1.
        triton_bin: Path to TRITON executable. Defaults to 'triton' on PATH.
    """

    def __init__(self, gpu: bool = True, n_gpus: int = 1, triton_bin: str = "triton"):
        self.gpu = gpu
        self.n_gpus = n_gpus
        self.triton_bin = triton_bin

    def run(self, terrain: str, flows, **kwargs) -> DepthGridSet:
        """
        Run TRITON simulation(s).

        TODO: implement adapter
        - Write TRITON input files from terrain + flow inputs
        - Execute TRITON binary (CPU or GPU mode)
        - Parse ASCII/binary output grids
        - Return as DepthGridSet
        """
        raise NotImplementedError(
            "TRITONEngine adapter not yet implemented. "
            "See docs/architecture.md for the integration spec."
        )

    @property
    def supports_ensemble(self) -> bool:
        return True  # TRITON's primary advantage

    @property
    def regulatory_grade(self) -> bool:
        return False  # Not FEMA-accepted

    @property
    def compute_backend(self) -> str:
        return "gpu" if self.gpu else "cpu"
