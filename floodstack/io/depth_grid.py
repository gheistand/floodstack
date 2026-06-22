"""
DepthGrid — common depth grid data model.

The currency between hydraulic engines and consequence engines.
Every hydraulic engine produces DepthGrids; every consequence engine consumes them.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class DepthGrid:
    """
    A georeferenced raster of water depths at a point in time.

    Units: meters (SI throughout FloodStack; convert at engine boundaries)
    """

    raster: np.ndarray          # 2D array of depth values (m)
    crs: str                    # EPSG code or WKT, e.g. "EPSG:4326"
    transform: object           # Affine transform (rasterio-compatible)
    scenario_id: str            # e.g. "100yr", "climate_2050_rcp85_run_12"
    engine: str = ""            # "triton" | "hec_ras" | etc.
    metadata: dict = field(default_factory=dict)

    @property
    def shape(self):
        return self.raster.shape

    @property
    def nodata_mask(self):
        return np.isnan(self.raster)

    def to_geotiff(self, path: str) -> None:
        """Export to GeoTIFF."""
        try:
            import rasterio
            from rasterio.transform import from_bounds
        except ImportError:
            raise ImportError("rasterio required for GeoTIFF export: pip install rasterio")

        with rasterio.open(
            path, "w",
            driver="GTiff",
            height=self.raster.shape[0],
            width=self.raster.shape[1],
            count=1,
            dtype=self.raster.dtype,
            crs=self.crs,
            transform=self.transform,
        ) as dst:
            dst.write(self.raster, 1)

    @classmethod
    def from_geotiff(cls, path: str, scenario_id: str = "") -> "DepthGrid":
        """Load from GeoTIFF."""
        try:
            import rasterio
        except ImportError:
            raise ImportError("rasterio required for GeoTIFF import: pip install rasterio")

        import warnings

        with rasterio.open(path) as src:
            # rasterio's Cython reader can set .shape on the returned ndarray,
            # which NumPy>=2.5 flags with a DeprecationWarning. The behavior is
            # internal to rasterio and harmless here; suppress only that exact
            # warning (narrowly scoped) rather than silencing anything broader.
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="Setting the shape on a NumPy array",
                    category=DeprecationWarning,
                )
                band = src.read(1)
            # Detach from rasterio's internal buffer into a clean float32 array.
            raster = np.array(band, dtype=np.float32, copy=True)
            return cls(
                raster=raster,
                crs=str(src.crs),
                transform=src.transform,
                scenario_id=scenario_id,
            )


@dataclass
class DepthGridSet:
    """
    A collection of DepthGrids — e.g., 50 climate scenarios or 4 return periods.
    """

    grids: list[DepthGrid] = field(default_factory=list)

    def __len__(self):
        return len(self.grids)

    def __iter__(self):
        return iter(self.grids)

    def __getitem__(self, key):
        return self.grids[key]

    def by_scenario(self, scenario_id: str) -> Optional[DepthGrid]:
        for g in self.grids:
            if g.scenario_id == scenario_id:
                return g
        return None

    def scenario_ids(self) -> list[str]:
        return [g.scenario_id for g in self.grids]
