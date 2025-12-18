# Web UI Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a browser-based interface for building healthcare scenarios and running simulations with shareable URLs.

**Architecture:** FastAPI server with Jinja2 templates, Alpine.js for client-side reactivity, and Tailwind CSS for styling. Sessions are content-addressed (hash of inputs = session ID) and stored in sharded directories. No build step, no npm.

**Tech Stack:** FastAPI, Jinja2, Alpine.js (CDN), Tailwind CSS (CDN), uvicorn

---

## Task 1: Add Web Dependencies

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add FastAPI and uvicorn dependencies**

Edit `pyproject.toml` to add web dependencies:

```toml
dependencies = [
    "pyyaml>=6.0",
    "numpy>=1.24",
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "jinja2>=3.0",
]
```

**Step 2: Install dependencies**

Run: `pip install -e .`
Expected: Success, new packages installed

**Step 3: Verify imports work**

Run: `python -c "import fastapi; import uvicorn; import jinja2; print('OK')"`
Expected: `OK`

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add fastapi, uvicorn, jinja2 for web UI"
```

---

## Task 2: Create Session Store Abstraction

**Files:**
- Create: `caca/web/__init__.py`
- Create: `caca/web/sessions.py`
- Create: `tests/test_web_sessions.py`

**Step 1: Write the failing test for SessionStore interface**

Create `tests/test_web_sessions.py`:

```python
# PURPOSE: Tests for web session storage

import pytest
import tempfile
from pathlib import Path
from caca.web.sessions import FileSessionStore


class TestFileSessionStore:
    def test_save_and_get_session(self, tmp_path):
        store = FileSessionStore(tmp_path)
        data = {"config": {"people": []}, "results": {"summary": {}}}

        store.save("abc123def456", data)
        result = store.get("abc123def456")

        assert result == data

    def test_get_nonexistent_returns_none(self, tmp_path):
        store = FileSessionStore(tmp_path)
        result = store.get("nonexistent")
        assert result is None

    def test_exists_returns_true_for_saved(self, tmp_path):
        store = FileSessionStore(tmp_path)
        store.save("abc123def456", {"test": "data"})
        assert store.exists("abc123def456") is True

    def test_exists_returns_false_for_missing(self, tmp_path):
        store = FileSessionStore(tmp_path)
        assert store.exists("nonexistent") is False

    def test_sharded_directory_structure(self, tmp_path):
        store = FileSessionStore(tmp_path)
        store.save("a3f8b2c1d4e5f6", {"test": "data"})

        # Should be stored at base/a3/f8/a3f8b2c1d4e5f6.json
        expected_path = tmp_path / "a3" / "f8" / "a3f8b2c1d4e5f6.json"
        assert expected_path.exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_sessions.py -v`
Expected: FAIL with "No module named 'caca.web'"

**Step 3: Create package init**

Create `caca/web/__init__.py`:

```python
# PURPOSE: Web UI package for Care Casino
```

**Step 4: Write minimal implementation**

Create `caca/web/sessions.py`:

```python
# PURPOSE: Session storage abstraction for web UI

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class SessionStore(ABC):
    """Abstract base class for session storage."""

    @abstractmethod
    def get(self, hash: str) -> Optional[dict]:
        """Get session by hash. Returns None if not found."""
        pass

    @abstractmethod
    def save(self, hash: str, data: dict) -> None:
        """Save session data."""
        pass

    @abstractmethod
    def exists(self, hash: str) -> bool:
        """Check if session exists."""
        pass


class FileSessionStore(SessionStore):
    """File-based session storage with two-level sharding."""

    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)

    def _path(self, hash: str) -> Path:
        """Get the file path for a given hash (two-level sharding)."""
        return self.base_dir / hash[:2] / hash[2:4] / f"{hash}.json"

    def get(self, hash: str) -> Optional[dict]:
        """Get session by hash."""
        path = self._path(hash)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    def save(self, hash: str, data: dict) -> None:
        """Save session data."""
        path = self._path(hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    def exists(self, hash: str) -> bool:
        """Check if session exists."""
        return self._path(hash).exists()
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_web_sessions.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add caca/web/__init__.py caca/web/sessions.py tests/test_web_sessions.py
git commit -m "feat(web): add session store abstraction with file backend"
```

---

## Task 3: Add Session Hash Computation

**Files:**
- Modify: `caca/web/sessions.py`
- Modify: `tests/test_web_sessions.py`

**Step 1: Write the failing test for hash computation**

Add to `tests/test_web_sessions.py`:

```python
from caca.web.sessions import compute_session_hash


class TestComputeSessionHash:
    def test_same_inputs_produce_same_hash(self):
        config1 = {"people": [{"name": "alice"}], "plans": ["plan1"]}
        config2 = {"people": [{"name": "alice"}], "plans": ["plan1"]}

        assert compute_session_hash(config1) == compute_session_hash(config2)

    def test_different_inputs_produce_different_hash(self):
        config1 = {"people": [{"name": "alice"}], "plans": ["plan1"]}
        config2 = {"people": [{"name": "bob"}], "plans": ["plan1"]}

        assert compute_session_hash(config1) != compute_session_hash(config2)

    def test_key_order_does_not_matter(self):
        config1 = {"plans": ["a"], "people": []}
        config2 = {"people": [], "plans": ["a"]}

        assert compute_session_hash(config1) == compute_session_hash(config2)

    def test_hash_is_hex_string(self):
        config = {"people": [], "plans": []}
        hash_val = compute_session_hash(config)

        assert isinstance(hash_val, str)
        assert len(hash_val) == 16
        assert all(c in "0123456789abcdef" for c in hash_val)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_sessions.py::TestComputeSessionHash -v`
Expected: FAIL with "cannot import name 'compute_session_hash'"

**Step 3: Write minimal implementation**

Add to `caca/web/sessions.py` at the top (after imports):

```python
import hashlib


def compute_session_hash(config: dict) -> str:
    """Compute a hash of the session config.

    The hash is deterministic: same inputs always produce the same hash.
    """
    canonical = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_sessions.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/web/sessions.py tests/test_web_sessions.py
git commit -m "feat(web): add content-addressed session hash computation"
```

---

## Task 4: Add Hash Validation

**Files:**
- Modify: `caca/web/sessions.py`
- Modify: `tests/test_web_sessions.py`

**Step 1: Write the failing test for hash validation**

Add to `tests/test_web_sessions.py`:

```python
from caca.web.sessions import is_valid_hash


class TestIsValidHash:
    def test_valid_16_char_hex(self):
        assert is_valid_hash("a3f8b2c1d4e5f6a7") is True

    def test_valid_32_char_hex(self):
        assert is_valid_hash("a3f8b2c1d4e5f6a7b8c9d0e1f2a3b4c5") is True

    def test_too_short(self):
        assert is_valid_hash("abc123") is False

    def test_too_long(self):
        assert is_valid_hash("a" * 65) is False

    def test_invalid_characters(self):
        assert is_valid_hash("a3f8b2c1d4e5f6g7") is False  # 'g' is invalid

    def test_path_traversal_attempt(self):
        assert is_valid_hash("../../../etc/passwd") is False

    def test_empty_string(self):
        assert is_valid_hash("") is False
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_sessions.py::TestIsValidHash -v`
Expected: FAIL with "cannot import name 'is_valid_hash'"

**Step 3: Write minimal implementation**

Add to `caca/web/sessions.py`:

```python
import re


def is_valid_hash(h: str) -> bool:
    """Validate that a string is a valid session hash.

    Valid hashes are 16-64 lowercase hex characters.
    This prevents path traversal attacks.
    """
    return bool(re.match(r"^[a-f0-9]{16,64}$", h))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_sessions.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/web/sessions.py tests/test_web_sessions.py
git commit -m "feat(web): add hash validation for security"
```

---

## Task 5: Create Rate Limiter

**Files:**
- Create: `caca/web/limiter.py`
- Create: `tests/test_web_limiter.py`

**Step 1: Write the failing test for rate limiter**

Create `tests/test_web_limiter.py`:

```python
# PURPOSE: Tests for simulation rate limiter

import pytest
import asyncio
from caca.web.limiter import SimulationLimiter, TooManyRequestsError


class TestSimulationLimiter:
    @pytest.mark.asyncio
    async def test_acquire_and_release(self):
        limiter = SimulationLimiter(max_concurrent=2)

        await limiter.acquire()
        await limiter.acquire()
        limiter.release()
        limiter.release()
        # Should not raise

    @pytest.mark.asyncio
    async def test_blocks_when_at_max_concurrent(self):
        limiter = SimulationLimiter(max_concurrent=1)

        await limiter.acquire()

        # Second acquire should block, so use timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(limiter.acquire(), timeout=0.1)

        limiter.release()

    @pytest.mark.asyncio
    async def test_raises_when_queue_full(self):
        limiter = SimulationLimiter(max_concurrent=1, max_queued=1)

        await limiter.acquire()

        # Start one waiting
        async def wait_for_acquire():
            await limiter.acquire()

        task = asyncio.create_task(wait_for_acquire())
        await asyncio.sleep(0.05)  # Let it start waiting

        # Third should raise immediately
        with pytest.raises(TooManyRequestsError):
            await limiter.acquire()

        limiter.release()
        await task
        limiter.release()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_limiter.py -v`
Expected: FAIL with "No module named 'caca.web.limiter'"

**Step 3: Write minimal implementation**

Create `caca/web/limiter.py`:

```python
# PURPOSE: Rate limiting for simulation requests

import asyncio


class TooManyRequestsError(Exception):
    """Raised when too many requests are queued."""
    pass


class SimulationLimiter:
    """Limits concurrent simulation requests.

    When max_concurrent simulations are running, new requests wait in queue.
    When max_queued requests are waiting, new requests are rejected immediately.
    """

    def __init__(self, max_concurrent: int = 4, max_queued: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queued = 0
        self.max_queued = max_queued
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Acquire a slot. Raises TooManyRequestsError if queue is full."""
        async with self._lock:
            if self.queued >= self.max_queued:
                raise TooManyRequestsError()
            self.queued += 1

        try:
            await self.semaphore.acquire()
        finally:
            async with self._lock:
                self.queued -= 1

    def release(self) -> None:
        """Release a slot."""
        self.semaphore.release()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_limiter.py -v`
Expected: All tests PASS

**Step 5: Add pytest-asyncio to dev dependencies**

Edit `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "pytest-cov>=4.0",
    "pytest-asyncio>=0.21",
]
```

Run: `pip install -e ".[dev]"`

**Step 6: Add asyncio mode to pytest config**

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
asyncio_mode = "auto"
```

**Step 7: Run tests again**

Run: `pytest tests/test_web_limiter.py -v`
Expected: All tests PASS

**Step 8: Commit**

```bash
git add caca/web/limiter.py tests/test_web_limiter.py pyproject.toml
git commit -m "feat(web): add rate limiter for simulation requests"
```

---

## Task 6: Create FastAPI App Structure

**Files:**
- Create: `caca/web/app.py`
- Create: `tests/test_web_app.py`

**Step 1: Write the failing test for app structure**

Create `tests/test_web_app.py`:

```python
# PURPOSE: Tests for FastAPI web application

import pytest
from fastapi.testclient import TestClient
from caca.web.app import create_app


class TestAppStructure:
    def test_app_creates_successfully(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        assert app is not None

    def test_landing_page_returns_200(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        response = client.get("/")

        assert response.status_code == 200

    def test_invalid_hash_returns_404(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        response = client.get("/nonexistenthash1")

        assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_app.py::TestAppStructure::test_app_creates_successfully -v`
Expected: FAIL with "cannot import name 'create_app'"

**Step 3: Create templates directory**

Run: `mkdir -p caca/web/templates`

**Step 4: Create minimal index template**

Create `caca/web/templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Care Casino</title>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <h1 class="text-3xl font-bold text-gray-800 mb-8">Care Casino</h1>
        <p class="text-gray-600">Healthcare cost simulator</p>
    </div>
</body>
</html>
```

**Step 5: Write minimal app implementation**

Create `caca/web/app.py`:

```python
# PURPOSE: FastAPI web application for Care Casino

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from caca.web.sessions import FileSessionStore, is_valid_hash


def create_app(sessions_dir: Path | str | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Care Casino")

    # Configure session storage
    sessions_path = Path(sessions_dir) if sessions_dir else Path(".caca-sessions")
    store = FileSessionStore(sessions_path)

    # Configure templates
    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @app.get("/", response_class=HTMLResponse)
    async def landing_page(request: Request):
        """Landing page - fresh editor."""
        return templates.TemplateResponse(
            "index.html",
            {"request": request},
        )

    @app.get("/{hash}", response_class=HTMLResponse)
    async def view_session(request: Request, hash: str):
        """View a saved session."""
        if not is_valid_hash(hash):
            return HTMLResponse(content="Not found", status_code=404)

        session = store.get(hash)
        if session is None:
            return HTMLResponse(content="Not found", status_code=404)

        return templates.TemplateResponse(
            "index.html",
            {"request": request, "session": session},
        )

    return app
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_web_app.py -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add caca/web/app.py caca/web/templates/index.html tests/test_web_app.py
git commit -m "feat(web): add FastAPI app with landing page and session routes"
```

---

## Task 7: Add /run Endpoint

**Files:**
- Modify: `caca/web/app.py`
- Modify: `tests/test_web_app.py`

**Step 1: Write the failing test for /run endpoint**

Add to `tests/test_web_app.py`:

```python
class TestRunEndpoint:
    def test_run_with_valid_config_returns_hash_and_results(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        config = {
            "people": [
                {
                    "name": "alice",
                    "usage": {"primary_care_visit": 2},
                }
            ],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {
                "primary_care_visit": {"min": 150, "max": 300},
            },
            "simulation": {
                "iterations": 100,
                "convergence_threshold_dollars": 100,
                "min_iterations": 100,
                "max_iterations": 100,
            },
        }

        response = client.post("/run", json=config)

        assert response.status_code == 200
        data = response.json()
        assert "hash" in data
        assert "results" in data
        assert len(data["hash"]) == 16

    def test_run_caches_results(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        config = {
            "people": [{"name": "bob", "usage": {}}],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {},
            "simulation": {
                "iterations": 10,
                "convergence_threshold_dollars": 100,
                "min_iterations": 10,
                "max_iterations": 10,
            },
        }

        response1 = client.post("/run", json=config)
        response2 = client.post("/run", json=config)

        assert response1.json()["hash"] == response2.json()["hash"]

    def test_run_with_invalid_config_returns_400(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        response = client.post("/run", json={"invalid": "config"})

        assert response.status_code == 400
        assert "error" in response.json()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_app.py::TestRunEndpoint -v`
Expected: FAIL with 404 (route doesn't exist yet)

**Step 3: Add imports and run endpoint**

Modify `caca/web/app.py` - add imports at top:

```python
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, ValidationError

from caca.web.sessions import FileSessionStore, is_valid_hash, compute_session_hash
from caca.web.limiter import SimulationLimiter, TooManyRequestsError
```

Add request model after imports:

```python
class RunRequest(BaseModel):
    """Request body for /run endpoint."""
    people: list[dict[str, Any]]
    plans: list[str]
    costs: dict[str, Any]
    simulation: dict[str, Any]
```

Add to `create_app` function before `return app`:

```python
    # Rate limiter
    limiter = SimulationLimiter(max_concurrent=4, max_queued=10)

    @app.post("/run")
    async def run_simulation(request: RunRequest):
        """Run simulation and return results."""
        try:
            await limiter.acquire()
        except TooManyRequestsError:
            return JSONResponse(
                status_code=503,
                content={"error": "Server busy, please try again shortly"},
                headers={"Retry-After": "5"},
            )

        try:
            # Compute hash from config
            config_dict = request.model_dump()
            session_hash = compute_session_hash(config_dict)

            # Check cache
            cached = store.get(session_hash)
            if cached is not None:
                return {"hash": session_hash, "results": cached["results"]}

            # Run simulation
            results = _run_simulation(config_dict)

            # Save session
            session_data = {
                "config": config_dict,
                "results": results,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            store.save(session_hash, session_data)

            return {"hash": session_hash, "results": results}

        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": str(e)},
            )
        finally:
            limiter.release()
```

Add helper function before `create_app`:

```python
def _run_simulation(config: dict) -> dict:
    """Run the simulation with the given config.

    This is a placeholder that will be connected to the real simulation runner.
    """
    from caca.simulation_runner import SimulationRunner
    from caca.models import CostRange
    from caca.loaders.plan_loader import load_plan_yaml
    from pathlib import Path

    # Load plans by name
    plans = []
    plans_dir = Path("plans/2026")
    for plan_name in config["plans"]:
        # Convert plan name to filename
        plan_file = plans_dir / f"{plan_name}.yaml"
        if plan_file.exists():
            with open(plan_file) as f:
                plans.append(load_plan_yaml(f))

    if not plans:
        raise ValueError("No valid plans found")

    # Convert costs to CostRange objects
    default_costs = {}
    for service, cost_def in config.get("costs", {}).items():
        if isinstance(cost_def, dict):
            default_costs[service] = CostRange(
                min_cost=cost_def.get("min", 0),
                max_cost=cost_def.get("max", cost_def.get("min", 0)),
            )

    # Build profiles
    profiles = {}
    household = []
    for person in config["people"]:
        name = person["name"]
        profiles[name] = person.get("usage", {})
        household.append({"name": name, "profile": name})

    # Run simulation
    sim_params = config["simulation"]
    runner = SimulationRunner(
        plans=plans,
        profiles=profiles,
        household=household,
        default_costs=default_costs,
        year=2025,
    )

    results = runner.run(
        iterations=sim_params.get("iterations", 1000),
        convergence_threshold_dollars=sim_params.get("convergence_threshold_dollars", 100),
        min_iterations=sim_params.get("min_iterations", 1000),
        max_iterations=sim_params.get("max_iterations", 100000),
    )

    return {
        "iterations": results.iterations,
        "converged": results.converged,
        "summary": results.summary,
    }
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_app.py -v`
Expected: Tests PASS (some may need adjustment based on actual plan loading)

**Step 5: Commit**

```bash
git add caca/web/app.py tests/test_web_app.py
git commit -m "feat(web): add /run endpoint with caching and rate limiting"
```

---

## Task 8: Add /{hash}.json Endpoint

**Files:**
- Modify: `caca/web/app.py`
- Modify: `tests/test_web_app.py`

**Step 1: Write the failing test**

Add to `tests/test_web_app.py`:

```python
class TestJsonEndpoint:
    def test_get_session_json(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        # First run a simulation
        config = {
            "people": [{"name": "alice", "usage": {}}],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {},
            "simulation": {
                "iterations": 10,
                "convergence_threshold_dollars": 100,
                "min_iterations": 10,
                "max_iterations": 10,
            },
        }
        run_response = client.post("/run", json=config)
        hash_val = run_response.json()["hash"]

        # Then get the JSON
        response = client.get(f"/{hash_val}.json")

        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "results" in data

    def test_nonexistent_json_returns_404(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        response = client.get("/a1b2c3d4e5f6g7h8.json")

        assert response.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_web_app.py::TestJsonEndpoint -v`
Expected: FAIL (route doesn't exist)

**Step 3: Add the JSON endpoint**

Add to `create_app` in `caca/web/app.py`, before the `/{hash}` route (order matters for FastAPI routing):

```python
    @app.get("/{hash}.json")
    async def get_session_json(hash: str):
        """Get raw session JSON."""
        # Strip .json suffix for validation
        hash_clean = hash.replace(".json", "")
        if not is_valid_hash(hash_clean):
            return JSONResponse(content={"error": "Not found"}, status_code=404)

        session = store.get(hash_clean)
        if session is None:
            return JSONResponse(content={"error": "Not found"}, status_code=404)

        return session
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_web_app.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/web/app.py tests/test_web_app.py
git commit -m "feat(web): add /{hash}.json endpoint for raw session data"
```

---

## Task 9: Add CLI Serve Command

**Files:**
- Modify: `caca/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Write the failing test**

Add to `tests/test_cli.py`:

```python
class TestServeCommand:
    def test_serve_subcommand_parses(self):
        args = parse_args(["serve"])
        assert args.command == "serve"
        assert args.port == 8000
        assert args.host == "127.0.0.1"

    def test_serve_with_port(self):
        args = parse_args(["serve", "--port", "9000"])
        assert args.port == 9000

    def test_serve_with_host(self):
        args = parse_args(["serve", "--host", "0.0.0.0"])
        assert args.host == "0.0.0.0"

    def test_serve_with_sessions_dir(self):
        args = parse_args(["serve", "--sessions-dir", "/tmp/sessions"])
        assert args.sessions_dir == "/tmp/sessions"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::TestServeCommand -v`
Expected: FAIL with error about unrecognized arguments

**Step 3: Add serve subcommand to CLI**

Modify `caca/cli.py` - add serve parser in `parse_args` after the validate parser:

```python
    # Serve subcommand
    serve_parser = subparsers.add_parser(
        "serve",
        help="Start web server",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    serve_parser.add_argument(
        "--sessions-dir",
        default=".caca-sessions",
        help="Directory for session storage (default: .caca-sessions)",
    )
```

**Step 4: Add serve command handler**

Add to `caca/cli.py`:

```python
def cmd_serve(args: argparse.Namespace) -> int:
    """Run the serve command."""
    import uvicorn
    from caca.web.app import create_app

    app = create_app(sessions_dir=args.sessions_dir)
    uvicorn.run(app, host=args.host, port=args.port)
    return 0
```

Update `main()`:

```python
def main() -> None:
    """Main entry point."""
    args = parse_args()

    if args.command == "generate":
        sys.exit(cmd_generate(args))
    elif args.command == "validate":
        sys.exit(cmd_validate(args))
    elif args.command == "serve":
        sys.exit(cmd_serve(args))
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: All tests PASS

**Step 6: Commit**

```bash
git add caca/cli.py tests/test_cli.py
git commit -m "feat(cli): add serve command for web server"
```

---

## Task 10: Create Interactive HTML Template

**Files:**
- Modify: `caca/web/templates/index.html`
- Modify: `caca/web/app.py`

**Step 1: Update template with Alpine.js components**

Replace `caca/web/templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Care Casino</title>
    <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen" x-data="simulator()">
    <div class="container mx-auto px-4 py-8 max-w-4xl">
        <!-- Header -->
        <div class="flex justify-between items-center mb-8">
            <h1 class="text-3xl font-bold text-gray-800">Care Casino</h1>
            <button
                @click="run()"
                :disabled="loading"
                class="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-semibold py-2 px-6 rounded-lg transition"
            >
                <span x-show="!loading">Run Simulation</span>
                <span x-show="loading">Running...</span>
            </button>
        </div>

        <!-- Error Banner -->
        <div x-show="error" class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
            <span x-text="error"></span>
        </div>

        <!-- People Section -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-semibold text-gray-700">People</h2>
                <button @click="addPerson()" class="text-blue-600 hover:text-blue-800 text-sm font-medium">
                    + Add Person
                </button>
            </div>

            <template x-for="(person, index) in people" :key="index">
                <div class="border border-gray-200 rounded-lg p-4 mb-4">
                    <div class="flex justify-between items-start mb-4">
                        <input
                            x-model="person.name"
                            type="text"
                            class="text-lg font-medium text-gray-800 border-b border-transparent hover:border-gray-300 focus:border-blue-500 focus:outline-none"
                            placeholder="Person name"
                        >
                        <button
                            @click="removePerson(index)"
                            x-show="people.length > 1"
                            class="text-red-500 hover:text-red-700 text-sm"
                        >
                            Remove
                        </button>
                    </div>

                    <div class="mb-3">
                        <label class="block text-sm font-medium text-gray-600 mb-1">Based on profile:</label>
                        <select
                            x-model="person.baseProfile"
                            @change="applyProfile(index)"
                            class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                        >
                            <option value="">-- Custom --</option>
                            <template x-for="profile in availableProfiles" :key="profile.name">
                                <option :value="profile.name" x-text="profile.name"></option>
                            </template>
                        </select>
                    </div>

                    <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm text-gray-600">Primary care visits</label>
                            <input
                                x-model.number="person.usage.primary_care_visit"
                                type="number"
                                min="0"
                                class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600">Specialist visits</label>
                            <input
                                x-model.number="person.usage.specialist_visit"
                                type="number"
                                min="0"
                                class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600">Labs</label>
                            <input
                                x-model.number="person.usage.labs"
                                type="number"
                                min="0"
                                class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                        </div>
                        <div>
                            <label class="block text-sm text-gray-600">Generic drugs</label>
                            <input
                                x-model.number="person.usage.tier_1_generic_drugs"
                                type="number"
                                min="0"
                                class="w-full border border-gray-300 rounded px-3 py-2 text-sm"
                            >
                        </div>
                    </div>
                </div>
            </template>
        </div>

        <!-- Plans Section -->
        <div class="bg-white rounded-lg shadow p-6 mb-6">
            <h2 class="text-xl font-semibold text-gray-700 mb-4">Plans</h2>
            <div class="space-y-2">
                <template x-for="plan in availablePlans" :key="plan">
                    <label class="flex items-center">
                        <input
                            type="checkbox"
                            :value="plan"
                            x-model="selectedPlans"
                            class="rounded border-gray-300 text-blue-600 mr-3"
                        >
                        <span class="text-gray-700" x-text="plan"></span>
                    </label>
                </template>
            </div>
        </div>

        <!-- Results Section -->
        <div x-show="results" class="bg-white rounded-lg shadow p-6">
            <div class="flex justify-between items-center mb-4">
                <h2 class="text-xl font-semibold text-gray-700">Results</h2>
                <div class="text-sm text-gray-500">
                    Share: <a :href="'/' + currentHash" class="text-blue-600 hover:underline" x-text="'/' + currentHash"></a>
                </div>
            </div>

            <div class="text-sm text-gray-600 mb-4">
                <span x-text="results?.iterations"></span> iterations,
                <span x-text="results?.converged ? 'converged' : 'did not converge'"></span>
            </div>

            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b">
                        <th class="text-left py-2">Plan</th>
                        <th class="text-right py-2">Expected Cost</th>
                        <th class="text-right py-2">95% CI</th>
                    </tr>
                </thead>
                <tbody>
                    <template x-for="(stats, planName) in results?.summary" :key="planName">
                        <tr class="border-b">
                            <td class="py-2" x-text="planName"></td>
                            <td class="text-right py-2" x-text="'$' + stats.expected_cost.toLocaleString(undefined, {maximumFractionDigits: 0})"></td>
                            <td class="text-right py-2 text-gray-500" x-text="'$' + stats.ci_95_low.toLocaleString(undefined, {maximumFractionDigits: 0}) + ' - $' + stats.ci_95_high.toLocaleString(undefined, {maximumFractionDigits: 0})"></td>
                        </tr>
                    </template>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        function simulator() {
            const initialData = window.CACA_DATA || {};

            return {
                people: initialData.session?.config?.people || [
                    { name: 'Person 1', baseProfile: '', usage: {} }
                ],
                selectedPlans: initialData.session?.config?.plans || [],
                availablePlans: initialData.availablePlans || [],
                availableProfiles: initialData.availableProfiles || [],
                defaultCosts: initialData.defaultCosts || {},
                results: initialData.session?.results || null,
                currentHash: initialData.currentHash || null,
                loading: false,
                error: null,

                addPerson() {
                    this.people.push({
                        name: `Person ${this.people.length + 1}`,
                        baseProfile: '',
                        usage: {}
                    });
                },

                removePerson(index) {
                    this.people.splice(index, 1);
                },

                applyProfile(index) {
                    const profileName = this.people[index].baseProfile;
                    const profile = this.availableProfiles.find(p => p.name === profileName);
                    if (profile) {
                        this.people[index].usage = { ...profile.usage };
                    }
                },

                async run() {
                    this.loading = true;
                    this.error = null;

                    try {
                        const response = await fetch('/run', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                people: this.people.map(p => ({
                                    name: p.name,
                                    usage: p.usage
                                })),
                                plans: this.selectedPlans,
                                costs: this.defaultCosts,
                                simulation: {
                                    iterations: 'auto',
                                    convergence_threshold_dollars: 100,
                                    min_iterations: 1000,
                                    max_iterations: 100000
                                }
                            })
                        });

                        if (!response.ok) {
                            const data = await response.json();
                            throw new Error(data.error || 'Simulation failed');
                        }

                        const data = await response.json();
                        this.results = data.results;
                        this.currentHash = data.hash;
                        history.pushState({}, '', '/' + data.hash);

                    } catch (e) {
                        this.error = e.message;
                    } finally {
                        this.loading = false;
                    }
                }
            };
        }
    </script>
</body>
</html>
```

**Step 2: Update app.py to pass data to template**

Modify the landing page and session routes in `caca/web/app.py`:

```python
def _get_available_plans() -> list[str]:
    """Get list of available plan filenames."""
    plans_dir = Path("plans/2026")
    if not plans_dir.exists():
        return []
    return [f.stem for f in plans_dir.glob("*.yaml")]


def _get_available_profiles() -> list[dict]:
    """Get list of available profiles with their usage data."""
    from caca.loaders.profile_loader import load_profile_yaml

    profiles_dir = Path("profiles")
    if not profiles_dir.exists():
        return []

    profiles = []
    for f in profiles_dir.glob("*.yaml"):
        with open(f) as fp:
            data = load_profile_yaml(fp)
            profiles.append({
                "name": data["name"],
                "usage": data["usage"],
            })
    return profiles


def _get_default_costs() -> dict:
    """Get default cost ranges."""
    return {
        "primary_care_visit": {"min": 150, "max": 300},
        "specialist_visit": {"min": 200, "max": 500},
        "labs": {"min": 100, "max": 500},
        "imaging": {"min": 500, "max": 2500},
        "outpatient_services": {"min": 2000, "max": 15000},
        "inpatient_services": {"min": 15000, "max": 75000},
        "emergency_room": {"min": 1500, "max": 5000},
        "urgent_care": {"min": 150, "max": 400},
        "tier_1_generic_drugs": {"min": 10, "max": 50},
        "tier_2_preferred_brand_drugs": {"min": 50, "max": 200},
    }
```

Update the landing page route:

```python
    @app.get("/", response_class=HTMLResponse)
    async def landing_page(request: Request):
        """Landing page - fresh editor."""
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "caca_data": {
                    "availablePlans": _get_available_plans(),
                    "availableProfiles": _get_available_profiles(),
                    "defaultCosts": _get_default_costs(),
                    "session": None,
                    "currentHash": None,
                },
            },
        )
```

Update the session view route:

```python
    @app.get("/{hash}", response_class=HTMLResponse)
    async def view_session(request: Request, hash: str):
        """View a saved session."""
        if not is_valid_hash(hash):
            return HTMLResponse(content="Not found", status_code=404)

        session = store.get(hash)
        if session is None:
            return HTMLResponse(content="Not found", status_code=404)

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "caca_data": {
                    "availablePlans": _get_available_plans(),
                    "availableProfiles": _get_available_profiles(),
                    "defaultCosts": _get_default_costs(),
                    "session": session,
                    "currentHash": hash,
                },
            },
        )
```

Update the template to use the passed data. Modify the script section of `index.html`:

```html
    <script>
        window.CACA_DATA = {{ caca_data | tojson | safe }};

        function simulator() {
            // ... rest unchanged
        }
    </script>
```

**Step 3: Test manually**

Run: `caca serve --port 8080`
Open: `http://localhost:8080`
Expected: See the UI with people editor and plans list

**Step 4: Commit**

```bash
git add caca/web/templates/index.html caca/web/app.py
git commit -m "feat(web): add interactive Alpine.js template with form components"
```

---

## Task 11: Add Error Page Template

**Files:**
- Create: `caca/web/templates/404.html`
- Modify: `caca/web/app.py`

**Step 1: Create 404 template**

Create `caca/web/templates/404.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Not Found - Care Casino</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen flex items-center justify-center">
    <div class="text-center">
        <h1 class="text-6xl font-bold text-gray-300 mb-4">404</h1>
        <h2 class="text-2xl font-semibold text-gray-700 mb-2">Scenario not found</h2>
        <p class="text-gray-500 mb-6">This scenario doesn't exist or has been removed.</p>
        <a href="/" class="text-blue-600 hover:text-blue-800 font-medium">
            Start a new scenario
        </a>
    </div>
</body>
</html>
```

**Step 2: Update app.py to use 404 template**

Modify the session view route in `caca/web/app.py`:

```python
    @app.get("/{hash}", response_class=HTMLResponse)
    async def view_session(request: Request, hash: str):
        """View a saved session."""
        if not is_valid_hash(hash):
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404,
            )

        session = store.get(hash)
        if session is None:
            return templates.TemplateResponse(
                "404.html",
                {"request": request},
                status_code=404,
            )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "caca_data": {
                    "availablePlans": _get_available_plans(),
                    "availableProfiles": _get_available_profiles(),
                    "defaultCosts": _get_default_costs(),
                    "session": session,
                    "currentHash": hash,
                },
            },
        )
```

**Step 3: Update tests to expect HTML 404**

Modify `tests/test_web_app.py`:

```python
    def test_invalid_hash_returns_404(self, tmp_path):
        app = create_app(sessions_dir=tmp_path)
        client = TestClient(app)

        response = client.get("/nonexistenthash1")

        assert response.status_code == 404
        assert "Scenario not found" in response.text
```

**Step 4: Run tests**

Run: `pytest tests/test_web_app.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add caca/web/templates/404.html caca/web/app.py tests/test_web_app.py
git commit -m "feat(web): add 404 error page template"
```

---

## Task 12: Integration Test for Full Flow

**Files:**
- Create: `tests/test_web_integration.py`

**Step 1: Write integration test**

Create `tests/test_web_integration.py`:

```python
# PURPOSE: Integration tests for web UI flow

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from caca.web.app import create_app


class TestWebIntegration:
    """Test full user flow through the web UI."""

    @pytest.fixture
    def app_with_plans(self, tmp_path):
        """Create app with test plans directory."""
        # The app looks for plans in plans/2026/, so we test with real plans
        return create_app(sessions_dir=tmp_path)

    def test_full_flow_landing_run_view(self, app_with_plans):
        """Test: landing page -> run simulation -> view results -> view by hash"""
        client = TestClient(app_with_plans)

        # 1. Landing page loads
        response = client.get("/")
        assert response.status_code == 200
        assert "Care Casino" in response.text

        # 2. Run simulation
        config = {
            "people": [
                {"name": "test_user", "usage": {"primary_care_visit": 3}}
            ],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {
                "primary_care_visit": {"min": 150, "max": 300},
            },
            "simulation": {
                "iterations": 100,
                "convergence_threshold_dollars": 500,
                "min_iterations": 100,
                "max_iterations": 100,
            },
        }
        response = client.post("/run", json=config)
        assert response.status_code == 200

        data = response.json()
        hash_val = data["hash"]
        assert "results" in data
        assert "summary" in data["results"]

        # 3. View session by hash
        response = client.get(f"/{hash_val}")
        assert response.status_code == 200
        assert hash_val in response.text  # Share link should show hash

        # 4. Get raw JSON
        response = client.get(f"/{hash_val}.json")
        assert response.status_code == 200
        json_data = response.json()
        assert json_data["config"] == config

    def test_same_config_returns_cached_hash(self, app_with_plans):
        """Test that identical configs return the same hash (content-addressed)."""
        client = TestClient(app_with_plans)

        config = {
            "people": [{"name": "cache_test", "usage": {}}],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {},
            "simulation": {
                "iterations": 50,
                "convergence_threshold_dollars": 500,
                "min_iterations": 50,
                "max_iterations": 50,
            },
        }

        response1 = client.post("/run", json=config)
        response2 = client.post("/run", json=config)

        assert response1.json()["hash"] == response2.json()["hash"]

    def test_different_config_returns_different_hash(self, app_with_plans):
        """Test that different configs return different hashes."""
        client = TestClient(app_with_plans)

        base_config = {
            "people": [{"name": "hash_test", "usage": {}}],
            "plans": ["bs-aca-silver-70-trio-hmo"],
            "costs": {},
            "simulation": {
                "iterations": 50,
                "convergence_threshold_dollars": 500,
                "min_iterations": 50,
                "max_iterations": 50,
            },
        }

        config1 = {**base_config, "people": [{"name": "alice", "usage": {}}]}
        config2 = {**base_config, "people": [{"name": "bob", "usage": {}}]}

        response1 = client.post("/run", json=config1)
        response2 = client.post("/run", json=config2)

        assert response1.json()["hash"] != response2.json()["hash"]
```

**Step 2: Run tests**

Run: `pytest tests/test_web_integration.py -v`
Expected: All tests PASS (assuming plans/2026/ exists with plans)

**Step 3: Commit**

```bash
git add tests/test_web_integration.py
git commit -m "test(web): add integration tests for full user flow"
```

---

## Task 13: Add Static File Serving (Optional CSS)

**Files:**
- Create: `caca/web/static/style.css`
- Modify: `caca/web/app.py`

**Step 1: Create static directory and optional CSS**

Create `caca/web/static/style.css`:

```css
/* PURPOSE: Custom styles for Care Casino (supplements Tailwind) */

/* Loading spinner animation */
@keyframes spin {
    to { transform: rotate(360deg); }
}

.animate-spin {
    animation: spin 1s linear infinite;
}

/* Custom focus styles */
input:focus, select:focus {
    outline: none;
    ring: 2px;
    ring-color: #3b82f6;
}
```

**Step 2: Mount static files in app**

Modify `caca/web/app.py` - add import:

```python
from fastapi.staticfiles import StaticFiles
```

Add in `create_app` after templates setup:

```python
    # Mount static files
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
```

**Step 3: Update template to reference static CSS**

Add to `<head>` in `index.html`:

```html
    <link rel="stylesheet" href="/static/style.css">
```

**Step 4: Commit**

```bash
git add caca/web/static/style.css caca/web/app.py caca/web/templates/index.html
git commit -m "feat(web): add static file serving and custom CSS"
```

---

## Task 14: Update .gitignore

**Files:**
- Modify: `.gitignore`

**Step 1: Add session storage to gitignore**

Add to `.gitignore`:

```
# Web UI session storage
.caca-sessions/
```

**Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .caca-sessions to gitignore"
```

---

## Task 15: Final Verification

**Step 1: Run all tests**

Run: `pytest -v`
Expected: All tests PASS

**Step 2: Manual smoke test**

Run: `caca serve`
Open: `http://localhost:8000`
Test:
1. Add a person
2. Select some plans
3. Click "Run Simulation"
4. Verify results appear
5. Copy the URL and open in new tab
6. Verify same results show

**Step 3: Verify no uncommitted changes**

Run: `git status`
Expected: Clean working tree

---

## Summary

This implementation creates a lightweight web UI for Care Casino with:

1. **Session storage** - Content-addressed sessions with two-level sharding
2. **Rate limiting** - Prevents server overload with 503 responses
3. **FastAPI backend** - Routes for landing, sessions, JSON, and simulation
4. **Alpine.js frontend** - Reactive form components without build step
5. **Shareable URLs** - Same inputs = same URL (pastebin-style)

Total: 15 tasks, following TDD with frequent commits.
