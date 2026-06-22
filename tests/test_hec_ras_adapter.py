"""
Tests for RASAgentEngine — the FloodStack <-> RAS Agent HTTP adapter.

These use a fake requests.Session so they run with no live RAS Agent server:
the whole submit -> poll -> depth-stats -> download -> DepthGrid flow is
exercised against canned responses, plus a real on-disk GeoTIFF for the
ft->m conversion check.
"""

from __future__ import annotations

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin  # noqa: E402

from floodstack.engines.hec_ras import RASAgentEngine, RASAgentError  # noqa: E402
from floodstack.io.depth_grid import DepthGridSet  # noqa: E402


# --------------------------------------------------------------------------- #
# Fake HTTP layer
# --------------------------------------------------------------------------- #
class FakeResponse:
    def __init__(self, status_code=200, json_data=None, content=b"", *, raises=False):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self._content = content
        self._raises = raises
        self.text = "" if json_data is None else str(json_data)

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RASAgentError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=1):
        yield self._content


class FakeSession:
    """Scripts the submit/poll/stats/download sequence deterministically."""

    def __init__(self, depth_tif_bytes):
        self.headers = {}
        self.depth_tif_bytes = depth_tif_bytes
        self.poll_calls = 0
        self.posted = []

    def post(self, url, json=None, timeout=None):
        self.posted.append((url, json))
        assert url.endswith("/api/pipeline")
        return FakeResponse(202, {"job_id": "job-123", "status": "running"})

    def get(self, url, params=None, timeout=None, stream=False, allow_redirects=True):
        if url.endswith("/api/jobs/job-123"):
            # First poll: running. Second: complete.
            self.poll_calls += 1
            status = "running" if self.poll_calls < 2 else "complete"
            return FakeResponse(200, {"id": "job-123", "status": status})
        if url.endswith("/results/depth-stats"):
            return FakeResponse(
                200,
                {
                    "job_id": "job-123",
                    "return_period_yr": (params or {}).get("return_period", 100),
                    "max_depth_m": 2.3,
                    "flood_area_km2": 12.5,
                    "output_files": ["depth_grid.tif", "wse_grid.tif", "flood_extent.gpkg"],
                },
            )
        if "/results/download/depth_grid.tif" in url:
            return FakeResponse(200, None, content=self.depth_tif_bytes)
        raise AssertionError(f"unexpected GET {url}")


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def depth_tif_bytes(tmp_path):
    """A tiny GeoTIFF of depths in FEET (so we can assert ft->m conversion)."""
    path = tmp_path / "depth_ft.tif"
    data = np.array([[0.0, 10.0], [20.0, np.nan]], dtype=np.float32)  # feet
    transform = from_origin(0, 2, 1, 1)
    with rasterio.open(
        path, "w", driver="GTiff", height=2, width=2, count=1,
        dtype="float32", crs="EPSG:4326", transform=transform, nodata=np.nan,
    ) as dst:
        dst.write(data, 1)
    return path.read_bytes()


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_engine_flags():
    eng = RASAgentEngine(api_url="http://x")
    assert eng.regulatory_grade is True
    assert eng.supports_ensemble is False
    assert eng.compute_backend == "cpu"
    assert RASAgentEngine(api_url="http://x", execution="hpc").compute_backend == "hpc"


def test_run_happy_path(depth_tif_bytes):
    session = FakeSession(depth_tif_bytes)
    eng = RASAgentEngine(
        api_url="http://localhost:8000",
        poll_interval_s=0,  # no real sleeping in tests
        session=session,
    )
    result = eng.run(terrain=(40.1, -88.2), flows=[100], name="unit-test")

    assert isinstance(result, DepthGridSet)
    assert result.scenario_ids() == ["100yr"]

    grid = result[0]
    assert grid.engine == "hec_ras"
    assert grid.metadata["job_id"] == "job-123"
    assert grid.metadata["units_converted"] == "ft->m"

    # 10 ft -> 3.048 m; 20 ft -> 6.096 m; nan stays nan.
    assert np.isclose(grid.raster[0, 1], 10.0 * 0.3048)
    assert np.isclose(grid.raster[1, 0], 20.0 * 0.3048)
    assert np.isnan(grid.raster[1, 1])

    # Submitted body sanity.
    _, body = session.posted[0]
    assert body["lat"] == 40.1 and body["lon"] == -88.2
    assert body["return_periods"] == [100]


def test_pour_point_required():
    eng = RASAgentEngine(api_url="http://x", session=FakeSession(b""))
    with pytest.raises(ValueError, match="pour point"):
        eng.run(terrain="not_a_point.tif", flows=[100])


def test_auth_headers_set():
    eng = RASAgentEngine(
        api_url="http://x",
        api_key="secret-key",
        cf_access=("cid", "csec"),
    )
    s = eng._get_session()
    assert s.headers["X-API-Key"] == "secret-key"
    assert s.headers["CF-Access-Client-Id"] == "cid"
    assert s.headers["CF-Access-Client-Secret"] == "csec"


def test_failed_job_raises(depth_tif_bytes):
    class FailSession(FakeSession):
        def get(self, url, params=None, timeout=None, stream=False, allow_redirects=True):
            if url.endswith("/api/jobs/job-123"):
                return FakeResponse(200, {"status": "error", "error_msg": "toolchain missing"})
            return super().get(url, params, timeout, stream, allow_redirects)

    eng = RASAgentEngine(api_url="http://x", poll_interval_s=0, session=FailSession(depth_tif_bytes))
    with pytest.raises(RASAgentError, match="toolchain missing"):
        eng.run(terrain=(40.1, -88.2), flows=[100])
