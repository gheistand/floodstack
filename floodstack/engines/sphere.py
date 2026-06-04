"""
InlandConsequencesEngine — adapter for fema-ffrd/inland-consequences.

Repo: https://github.com/fema-ffrd/inland-consequences
Docs: https://fema-ffrd.github.io/inland-consequences/

Note on naming:
  SPHERE (github.com/Niyam-Projects/sphere) is the contractor/proprietary
  implementation built by Troy Schmidt at Niyam Projects. It implements the
  same HAZUS flood loss methodology.

  inland-consequences is the open-source FEMA FFRD release — the one
  FloodStack integrates. Troy's deep knowledge of SPHERE informs this
  integration and makes him the ideal collaboration contact.

inland-consequences runs the FEMA HAZUS flood loss methodology using
modern infrastructure: Python + DuckDB. Supports both coastal and inland
(riverine/pluvial) consequence modeling.

Use for:
  - Structure-level damage estimation from depth grids
  - Annualized average loss (AAL) calculations
  - Probabilistic risk curves (P(loss > x) vs. loss)
  - Portfolio-level consequence screening
"""

from .base import ConsequenceEngine
from ..io.depth_grid import DepthGridSet


class InlandConsequencesEngine(ConsequenceEngine):
    """
    Adapter for fema-ffrd/inland-consequences.

    Args:
        depth_damage:  Depth-damage function set. Default 'hazus_fema'.
        occupancy:     Occupancy classification schema. Default 'hazus'.
    """

    def __init__(
        self,
        depth_damage: str = "hazus_fema",
        occupancy: str = "hazus",
    ):
        self.depth_damage = depth_damage
        self.occupancy = occupancy

    def run(self, depth_grids: DepthGridSet, structures, **kwargs):
        """
        Apply HAZUS flood consequence estimation to depth grids.

        Args:
            depth_grids: DepthGridSet (one grid per scenario/return period)
            structures:  Path to structure inventory
                         - NSI (National Structure Inventory) GeoJSON or GeoParquet
                         - Custom structure layer with required fields
            **kwargs:    Additional inland-consequences options

        Returns:
            ConsequenceResult with:
              - structure_damages: per-structure depth + damage per scenario
              - summary: damage totals by scenario
              - risk_curve: exceedance probability vs. loss
              - annualized_loss: AAL scalar

        TODO: implement adapter
        - Sample depth grids at structure locations (point extraction)
        - Pass depth values + structure inventory to inland-consequences
        - Parse output (DuckDB results)
        - Return as ConsequenceResult
        """
        raise NotImplementedError(
            "InlandConsequencesEngine adapter not yet implemented. "
            "See docs/architecture.md for the integration spec. "
            "Target: github.com/fema-ffrd/inland-consequences. "
            "Collaboration with Troy Schmidt (Niyam Projects) planned — "
            "his SPHERE knowledge directly informs this integration."
        )


# Alias for backward compatibility and discoverability
SPHEREEngine = InlandConsequencesEngine
