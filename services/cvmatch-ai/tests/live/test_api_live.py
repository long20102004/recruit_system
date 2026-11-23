"""Kich ban API that (HTTP) vao server demo dang chay. Bo qua mac dinh; chay:

    python -m cvmatch.cli demo seed && python -m cvmatch.cli demo serve     # cua so 1
    python -m pytest -m live                                                  # cua so 2

Dia chi server: CVMATCH_API_URL (mac dinh http://127.0.0.1:8090). Can data/demo/state.json (tu `demo seed`).
"""

import os

import httpx
import pytest

from cvmatch.demo.scenarios import SCENARIOS, Runner
from cvmatch.demo.seed import load_state

pytestmark = pytest.mark.live
API = os.environ.get("CVMATCH_API_URL", "http://127.0.0.1:8090")


@pytest.fixture(scope="module")
def runner():
    try:
        state = load_state()
    except FileNotFoundError as e:
        pytest.skip(str(e))
    try:
        httpx.get(f"{API}/health", timeout=3).raise_for_status()
    except Exception:  # noqa: BLE001
        pytest.skip(f"khong ket noi duoc API {API} - chay `cvmatch demo serve`")
    r = Runner(API, state)
    yield r
    r.cleanup()


@pytest.mark.parametrize("name", [n for n, _ in SCENARIOS])
def test_scenario(runner, name):
    fn = dict(SCENARIOS)[name]
    print(fn(runner))
