# FloodStack Architecture

## Core Concept

FloodStack is an **orchestration layer**, not a hydraulic model. It doesn't compute water surface elevations or depth-damage functions itself — it coordinates the tools that do, translates data between them, and presents a unified interface.

The central abstraction is the **depth grid**: a georeferenced raster of water depths at a point in time. Every hydraulic engine produces depth grids; every consequence engine consumes them. FloodStack owns this translation.

---

## Pipeline

```python
from floodstack import Pipeline
from floodstack.engines import TRITONEngine, RASAgentEngine, SPHEREEngine

# Example: climate ensemble → risk curve
pipeline = Pipeline(
    hydraulic=TRITONEngine(gpu=True),
    consequence=SPHEREEngine(),
)

results = pipeline.run(
    terrain="path/to/dem.tif",
    flows=climate_scenario_flows,  # list of 50 flow hydrographs
    structures="path/to/nsiBuildingFootprints.parquet",
    mode="ensemble",
)

results.risk_curve()       # Exceedance probability vs. damage
results.export_geotiff()   # Depth grid stack
results.export_parquet()   # Structure-level damage table
```

```python
# Example: regulatory FIRM work + consequence summary
pipeline = Pipeline(
    hydraulic=RASAgentEngine(),
    consequence=SPHEREEngine(),
)

results = pipeline.run(
    ras_project="path/to/project.prj",
    return_periods=[10, 50, 100, 500],
    structures="path/to/nsiBuildingFootprints.parquet",
    mode="regulatory",
)

results.flood_map()           # FEMA-quality depth grid per return period
results.consequence_table()   # Damage by structure, by return period
results.annualized_loss()     # AAL across return periods
```

---

## Engine Interface

All hydraulic engines implement a common interface:

```python
class HydraulicEngine(ABC):
    def run(self, terrain, flows, **kwargs) -> DepthGridSet:
        """Run simulation, return depth grids."""
        ...

    def supports_ensemble(self) -> bool: ...
    def supports_regulatory(self) -> bool: ...
    def compute_backend(self) -> str: ...  # "cpu" | "gpu" | "hpc"
```

Similarly, consequence engines:

```python
class ConsequenceEngine(ABC):
    def run(self, depth_grids: DepthGridSet, structures, **kwargs) -> ConsequenceResult:
        """Apply consequence model to depth grids."""
        ...
```

This means TRITON, HEC-RAS, or any future engine (AdH, Delft3D, etc.) plugs in cleanly.

---

## Data Model

### DepthGrid
```python
@dataclass
class DepthGrid:
    raster: np.ndarray        # depth values (meters)
    crs: str                  # coordinate reference system
    transform: Affine         # georeferencing
    scenario_id: str          # return period, climate scenario, timestamp
    metadata: dict            # engine, runtime, inputs, etc.
```

### DepthGridSet
A collection of DepthGrids — e.g., 50 climate scenarios or 4 return periods.

### ConsequenceResult
```python
@dataclass
class ConsequenceResult:
    structure_damages: gpd.GeoDataFrame   # per-structure depth + damage
    summary: pd.DataFrame                  # by scenario
    risk_curve: pd.DataFrame              # exceedance probability vs. damage
    annualized_loss: float
```

---

## IO Layer

Format translation is the unsexy but critical part.

| Source | Format | Target | Notes |
|---|---|---|---|
| TRITON output | ASCII/binary raster | DepthGrid | Grid spacing, CRS handling |
| HEC-RAS output | HDF5 (2D mesh) | DepthGrid | Unstructured → structured resampling |
| SPHERE input | GeoParquet / DuckDB | DepthGrid sampling at structure locations | |
| NSI structures | GeoJSON / Parquet | Structures layer | National Structure Inventory |

---

## Engine Selection Logic

The pipeline selects engines based on job type:

```python
def select_engine(mode, regulatory_required, ensemble_size, gpu_available):
    if regulatory_required:
        return RASAgentEngine()  # Only FEMA-accepted engine
    elif ensemble_size > 10 and gpu_available:
        return TRITONEngine(gpu=True)
    elif ensemble_size > 1:
        return TRITONEngine(gpu=False)
    else:
        return RASAgentEngine()  # Default for single high-fidelity run
```

User can always override.

---

## Triage Workflow

For large portfolios (e.g., CHAMP's 5,300+ stream miles):

1. **TRITON fast pass** — run all reaches with simplified DEM + median flows
2. **Score reaches** — by inundation extent, structure exposure, depth
3. **Prioritize** — return ranked reach list with TRITON-estimated consequences via SPHERE
4. **Formal runs** — RAS Agent runs HEC-RAS on top N reaches only

This makes portfolio-scale flood risk tractable without sacrificing regulatory quality where it matters.

---

## Roadmap

See `docs/roadmap.md`
