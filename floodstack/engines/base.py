"""
Abstract base classes for FloodStack engines.
"""

from abc import ABC, abstractmethod
from ..io.depth_grid import DepthGridSet


class HydraulicEngine(ABC):
    """Base class for all hydraulic simulation engines."""

    @abstractmethod
    def run(self, terrain: str, flows, **kwargs) -> DepthGridSet:
        """
        Run hydraulic simulation.

        Args:
            terrain: Path to DEM/terrain file
            flows:   Flow inputs (hydrograph, return period flows, etc.)
            **kwargs: Engine-specific options

        Returns:
            DepthGridSet with one DepthGrid per scenario/return period
        """
        ...

    @property
    @abstractmethod
    def supports_ensemble(self) -> bool:
        """True if this engine can efficiently run many scenarios."""
        ...

    @property
    @abstractmethod
    def regulatory_grade(self) -> bool:
        """True if this engine produces FEMA-accepted outputs."""
        ...

    @property
    def compute_backend(self) -> str:
        """'cpu' | 'gpu' | 'hpc'"""
        return "cpu"


class ConsequenceEngine(ABC):
    """Base class for all consequence/damage estimation engines."""

    @abstractmethod
    def run(self, depth_grids: DepthGridSet, structures, **kwargs):
        """
        Apply consequence model to depth grids.

        Args:
            depth_grids: DepthGridSet from a hydraulic engine
            structures:  Path to structure inventory (NSI GeoJSON/Parquet, etc.)
            **kwargs:    Engine-specific options

        Returns:
            ConsequenceResult
        """
        ...
