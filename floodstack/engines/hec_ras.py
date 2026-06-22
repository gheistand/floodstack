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

Integration model
-----------------
This adapter talks to a *running RAS Agent API server* over HTTP rather than
importing RAS Agent's Python internals. That keeps FloodStack a thin, decoupled
orchestrator: RAS Agent can run on a different machine (a Linux prep box, an HPC
login node, a container) and FloodStack just drives it. The only coupling is the
public REST contract.

Flow (pour-point / "click-to-run" pipeline):
    POST /api/pipeline              -> 202 + job_id
    GET  /api/jobs/{job_id}         -> poll until status == "complete"
    GET  /api/jobs/{id}/results/depth-stats?return_period=RP
                                    -> output_files per return period
    GET  /api/jobs/{id}/results/download/{filename}
                                    -> the depth_grid.tif for that RP
    -> DepthGrid.from_geotiff(...)  -> assembled into a DepthGridSet

Units: RAS Agent emits depth rasters in FEET (HEC-RAS US-survey-foot
convention). FloodStack is SI (meters) throughout, so depths are converted at
this engine boundary (see ``_FT_TO_M``).
"""

from __future__ import annotations

import os
import tempfile
import time
from typing import Iterable, Optional

import numpy as np

from .base import HydraulicEngine
from ..io.depth_grid import DepthGrid, DepthGridSet


# HEC-RAS authors results in US survey feet; FloodStack is SI (meters).
_FT_TO_M = 0.3048

# Terminal job states reported by RAS Agent's runner.
_DONE_STATES = {"complete", "completed", "done", "success"}
_FAIL_STATES = {"error", "failed", "cancelled", "canceled"}

# Candidate depth-raster filenames RAS Agent may produce, in preference order.
_DEPTH_FILE_CANDIDATES = ("depth_grid.tif", "depth.tif", "wse_depth.tif")


class RASAgentError(RuntimeError):
    """Raised when a RAS Agent run fails or the API is unreachable."""


class RASAgentEngine(HydraulicEngine):
    """
    Adapter for HEC-RAS via the RAS Agent REST API.

    Args:
        api_url:    Base URL of a running RAS Agent API, e.g.
                    "https://ras-agent-api.champ-pm.app" or
                    "http://localhost:8000". Falls back to the
                    ``RAS_AGENT_API_URL`` env var, then localhost.
        api_key:    Value for the ``X-API-Key`` header (origin auth). Falls back
                    to the ``RAS_AGENT_API_KEY`` env var.
        cf_access:  Optional (client_id, client_secret) tuple for a Cloudflare
                    Access service token. When the API host sits behind CF
                    Access (edge gate), these are sent as
                    ``CF-Access-Client-Id`` / ``CF-Access-Client-Secret``.
                    Falls back to RAS_AGENT_CF_CLIENT_ID / _SECRET env vars.
        execution:  "local" (run on the API host) or "hpc" (submit the solve to
                    the configured Slurm cluster). "hpc" implies a real run.
        mock:       When True, ask RAS Agent for a no-toolchain demo run. Handy
                    for wiring/integration tests; not a real hydraulic result.
        poll_interval_s / timeout_s: job polling cadence and ceiling.
        session:    Optional pre-built ``requests.Session`` (for tests/mocks).
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        cf_access: Optional[tuple[str, str]] = None,
        execution: str = "local",
        mock: bool = False,
        poll_interval_s: float = 10.0,
        timeout_s: float = 6 * 60 * 60,  # 6h ceiling for a real cluster solve
        session=None,
    ):
        if execution not in ("local", "hpc"):
            raise ValueError("execution must be 'local' or 'hpc'")

        self.api_url = (
            api_url
            or os.environ.get("RAS_AGENT_API_URL")
            or "http://localhost:8000"
        ).rstrip("/")
        self.api_key = api_key or os.environ.get("RAS_AGENT_API_KEY")

        if cf_access is None:
            cid = os.environ.get("RAS_AGENT_CF_CLIENT_ID")
            csec = os.environ.get("RAS_AGENT_CF_CLIENT_SECRET")
            cf_access = (cid, csec) if cid and csec else None
        self.cf_access = cf_access

        self.execution = execution
        self.mock = mock
        self.poll_interval_s = poll_interval_s
        self.timeout_s = timeout_s
        self._session = session  # lazy-init in _get_session()

    # ------------------------------------------------------------------ #
    # HydraulicEngine interface
    # ------------------------------------------------------------------ #
    def run(self, terrain: str, flows, **kwargs) -> DepthGridSet:
        """
        Run HEC-RAS via RAS Agent and return a DepthGridSet (one grid per
        return period).

        RAS Agent's pour-point pipeline is driven by a geographic *pour point*
        (lat/lon), not a pre-supplied DEM — it fetches/derives terrain itself.
        FloodStack's generic ``terrain``/``flows`` signature is mapped as:

          - pour point: ``kwargs['lat']`` / ``kwargs['lon']`` (preferred), else
            a ``(lat, lon)`` 2-tuple passed as ``terrain`` for convenience.
          - return periods: ``flows`` may be an iterable of ints (e.g.
            ``[2, 10, 100, 500]``); falls back to RAS Agent workflow defaults
            when None/empty.

        Other accepted kwargs: ``name`` (run label).
        """
        lat, lon = self._resolve_pour_point(terrain, kwargs)
        return_periods = self._resolve_return_periods(flows)
        name = kwargs.get("name") or f"floodstack_{int(time.time())}"

        job_id = self._submit_pipeline(name, lat, lon, return_periods)
        self._await_completion(job_id)
        return self._collect_depth_grids(job_id, return_periods)

    @property
    def supports_ensemble(self) -> bool:
        return False  # Not efficient for large ensembles; use TRITON

    @property
    def regulatory_grade(self) -> bool:
        return True  # FEMA-accepted; only engine with this flag

    @property
    def compute_backend(self) -> str:
        return "hpc" if self.execution == "hpc" else "cpu"

    # ------------------------------------------------------------------ #
    # Input normalization
    # ------------------------------------------------------------------ #
    @staticmethod
    def _resolve_pour_point(terrain, kwargs) -> tuple[float, float]:
        if "lat" in kwargs and "lon" in kwargs:
            return float(kwargs["lat"]), float(kwargs["lon"])
        if (
            isinstance(terrain, (tuple, list))
            and len(terrain) == 2
            and all(isinstance(v, (int, float)) for v in terrain)
        ):
            return float(terrain[0]), float(terrain[1])
        raise ValueError(
            "RASAgentEngine needs a pour point: pass lat=<y>, lon=<x> "
            "(or terrain=(lat, lon)). RAS Agent derives terrain from the "
            "pour point itself."
        )

    @staticmethod
    def _resolve_return_periods(flows) -> Optional[list[int]]:
        if flows is None:
            return None
        if isinstance(flows, Iterable) and not isinstance(flows, (str, bytes)):
            rps = [int(x) for x in flows]
            return rps or None
        # A single scalar return period is allowed too.
        try:
            return [int(flows)]
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # HTTP plumbing
    # ------------------------------------------------------------------ #
    def _get_session(self):
        if self._session is not None:
            return self._session
        try:
            import requests
        except ImportError as exc:  # pragma: no cover - dependency hint
            raise ImportError(
                "requests is required for RASAgentEngine: pip install requests"
            ) from exc
        s = requests.Session()
        headers = {}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        if self.cf_access:
            cid, csec = self.cf_access
            headers["CF-Access-Client-Id"] = cid
            headers["CF-Access-Client-Secret"] = csec
        s.headers.update(headers)
        self._session = s
        return s

    def _url(self, path: str) -> str:
        return f"{self.api_url}{path}"

    def _submit_pipeline(
        self, name: str, lat: float, lon: float, return_periods: Optional[list[int]]
    ) -> str:
        body = {
            "name": name,
            "lat": lat,
            "lon": lon,
            "mock": self.mock,
            "execution": self.execution,
        }
        if return_periods:
            body["return_periods"] = return_periods

        resp = self._get_session().post(
            self._url("/api/pipeline"), json=body, timeout=60
        )
        if resp.status_code != 202:
            raise RASAgentError(
                f"Pipeline submit failed ({resp.status_code}): {resp.text[:500]}"
            )
        data = resp.json()
        job_id = data.get("job_id")
        if not job_id:
            raise RASAgentError(f"No job_id in pipeline response: {data}")
        return job_id

    def _await_completion(self, job_id: str) -> dict:
        deadline = time.time() + self.timeout_s
        last_status = None
        while time.time() < deadline:
            resp = self._get_session().get(
                self._url(f"/api/jobs/{job_id}"), timeout=60
            )
            if resp.status_code == 404:
                raise RASAgentError(f"Job vanished: {job_id}")
            resp.raise_for_status()
            job = resp.json()
            status = (job.get("status") or "").lower()
            last_status = status
            if status in _DONE_STATES:
                return job
            if status in _FAIL_STATES:
                raise RASAgentError(
                    f"RAS Agent job {job_id} {status}: "
                    f"{job.get('error_msg') or 'no error message'}"
                )
            time.sleep(self.poll_interval_s)
        raise RASAgentError(
            f"RAS Agent job {job_id} did not finish within "
            f"{self.timeout_s:.0f}s (last status: {last_status})"
        )

    # ------------------------------------------------------------------ #
    # Result assembly
    # ------------------------------------------------------------------ #
    def _collect_depth_grids(
        self, job_id: str, return_periods: Optional[list[int]]
    ) -> DepthGridSet:
        # If caller did not pin return periods, ask the server what it produced.
        rps = return_periods or self._discover_return_periods(job_id)
        grids: list[DepthGrid] = []
        for rp in rps:
            grid = self._fetch_depth_grid(job_id, rp)
            if grid is not None:
                grids.append(grid)
        if not grids:
            raise RASAgentError(
                f"Job {job_id} completed but no depth rasters were retrievable."
            )
        return DepthGridSet(grids=grids)

    def _discover_return_periods(self, job_id: str) -> list[int]:
        resp = self._get_session().get(
            self._url(f"/api/jobs/{job_id}/results/depth-stats"), timeout=60
        )
        resp.raise_for_status()
        rp = resp.json().get("return_period_yr")
        return [int(rp)] if rp else []

    def _depth_stats(self, job_id: str, rp: int) -> dict:
        resp = self._get_session().get(
            self._url(f"/api/jobs/{job_id}/results/depth-stats"),
            params={"return_period": rp},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()

    def _fetch_depth_grid(self, job_id: str, rp: int) -> Optional[DepthGrid]:
        stats = self._depth_stats(job_id, rp)
        output_files = stats.get("output_files") or []

        filename = next(
            (c for c in _DEPTH_FILE_CANDIDATES if c in output_files),
            None,
        )
        if filename is None:
            filename = next(
                (f for f in output_files if f.endswith(".tif") and "depth" in f.lower()),
                None,
            )
        if filename is None:
            return None

        local_tif = self._download(job_id, filename)
        try:
            grid = DepthGrid.from_geotiff(local_tif, scenario_id=f"{rp}yr")
        finally:
            try:
                os.unlink(local_tif)
            except OSError:
                pass

        # Convert HEC-RAS feet -> FloodStack meters at the engine boundary.
        with np.errstate(invalid="ignore"):
            grid.raster = (grid.raster.astype(np.float32)) * _FT_TO_M
        grid.engine = "hec_ras"
        grid.metadata.update(
            {
                "source": "ras-agent",
                "job_id": job_id,
                "return_period_yr": rp,
                "api_url": self.api_url,
                "execution": self.execution,
                "units_converted": "ft->m",
                "max_depth_m": stats.get("max_depth_m"),
                "flood_area_km2": stats.get("flood_area_km2"),
            }
        )
        return grid

    def _download(self, job_id: str, filename: str) -> str:
        resp = self._get_session().get(
            self._url(f"/api/jobs/{job_id}/results/download/{filename}"),
            timeout=300,
            stream=True,
            allow_redirects=True,  # follows 302 -> presigned R2 URL when configured
        )
        if resp.status_code != 200:
            raise RASAgentError(
                f"Download failed for {filename} ({resp.status_code})"
            )
        suffix = os.path.splitext(filename)[1] or ".tif"
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="floodstack_ras_")
        with os.fdopen(fd, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
        return path
