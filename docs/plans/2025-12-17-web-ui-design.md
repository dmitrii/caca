# Web UI Design

A browser-based interface for building healthcare scenarios and running simulations.

## Goals

1. Allow users to build profiles, select plans, adjust costs, and run simulations
2. Shareable URLs for scenarios (pastebin-style)
3. Cache-backed persistence (no accounts needed)
4. Lightweight server footprint
5. Adaptable to serverless deployment

## Tech Stack

- **FastAPI** - Python web framework
- **Alpine.js** - Lightweight client-side reactivity (~15KB)
- **Tailwind CSS** - Utility-first styling
- **Jinja2** - Server-side templates

No build step, no npm, minimal JavaScript.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Browser                             │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Alpine.js + Tailwind CSS                        │    │
│  │  - Profile editor (dynamic forms)                │    │
│  │  - Plan selector (checkboxes)                    │    │
│  │  - Cost adjuster (key-value editor)              │    │
│  │  - Results display (tables, histograms)          │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Server                         │
│                                                          │
│  GET  /            Landing page (fresh editor)          │
│  GET  /{hash}      Load saved session + results         │
│  GET  /{hash}.json Raw session JSON                     │
│  POST /run         Run simulation, return {hash, results}│
│                                                          │
│                           │                              │
│                           ▼                              │
│              ┌──────────────────────┐                   │
│              │    SessionStore      │                   │
│              │    (abstraction)     │                   │
│              └──────────────────────┘                   │
│                      │          │                        │
│          ┌───────────┘          └───────────┐           │
│          ▼                                  ▼           │
│  ┌──────────────────┐           ┌──────────────────┐   │
│  │ FileSessionStore │           │  S3SessionStore  │   │
│  │ .caca-sessions/  │           │  (future)        │   │
│  └──────────────────┘           └──────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## URL Structure

- `GET /` - Landing page, redirects to `/{hash}` if cookie exists
- `GET /{hash}` - View saved config + results, editable
- `GET /{hash}.json` - Raw JSON of session
- `POST /run` - Submit config, returns `{hash, results}`

Session ID = cache key = hash of canonical inputs. Same inputs from different users produce the same URL.

## Session Model

**Key principle:** A session is persisted when simulation runs. No run = nothing saved.

**Flow:**

1. User visits `/` → fresh editor (cookie tracks last session for redirect)
2. User edits config → client-side only, nothing saved yet
3. User clicks "Run" → POST to `/run` with config
4. Server computes hash of inputs → checks cache
   - Cache hit: return results instantly
   - Cache miss: run simulation, store results
5. Browser updates URL to `/{hash}`, shows results
6. User gets shareable URL
7. Another user visits `/{hash}` → sees same config + results
8. Either user edits + runs → new hash if inputs differ, same hash if identical

## Storage

**Directory structure (two-level sharding):**

```
.caca-sessions/
  a3/
    f8/
      a3f8b2c1d4e5f6.json
```

**Session file format:**

```json
{
  "config": {
    "people": [...],
    "plans": [...],
    "costs": {...}
  },
  "results": {...},
  "created_at": "2025-12-17T10:30:00Z",
  "accessed_at": "2025-12-17T10:30:00Z"
}
```

**Cookie:**

```
caca_last_session={hash}
```

Tracks most recent session for redirect convenience. No auth, no ownership.

## Storage Abstraction

Interface for swappable backends (file, S3, etc.):

```python
from abc import ABC, abstractmethod
from typing import Optional

class SessionStore(ABC):
    @abstractmethod
    async def get(self, hash: str) -> Optional[dict]:
        """Get session by hash. Returns None if not found."""
        pass

    @abstractmethod
    async def save(self, hash: str, data: dict) -> None:
        """Save session data."""
        pass

    @abstractmethod
    async def exists(self, hash: str) -> bool:
        """Check if session exists."""
        pass
```

**File implementation (default):**

```python
class FileSessionStore(SessionStore):
    def __init__(self, base_dir: Path = Path(".caca-sessions")):
        self.base_dir = base_dir

    def _path(self, hash: str) -> Path:
        return self.base_dir / hash[:2] / hash[2:4] / f"{hash}.json"

    async def get(self, hash: str) -> Optional[dict]:
        path = self._path(hash)
        if not path.exists():
            return None
        return json.loads(path.read_text())

    async def save(self, hash: str, data: dict) -> None:
        path = self._path(hash)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))

    async def exists(self, hash: str) -> bool:
        return self._path(hash).exists()
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Care Casino                              [Run Simulation]  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─── People ───────────────────────────────────────────┐  │
│  │ [+ Add Person]                                        │  │
│  │                                                       │  │
│  │ ┌─ Alice ──────────────────────────────────────────┐ │  │
│  │ │ Based on: [healthy-young-adult ▼]        [Remove] │ │  │
│  │ │                                                   │ │  │
│  │ │ Primary care visits:  [3    ]                     │ │  │
│  │ │ Specialist visits:    [1    ]                     │ │  │
│  │ │ Labs:                 [2    ]                     │ │  │
│  │ │ Emergency room:       [+ Add detailed entry]      │ │  │
│  │ └───────────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Plans ────────────────────────────────────────────┐  │
│  │ ☑ BS Bronze 60 HDHP PPO                              │  │
│  │ ☑ BS Silver 70 Trio HMO                              │  │
│  │ ☐ BS Gold 80 Trio HMO                                │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌─── Costs [▼ collapsed by default] ───────────────────┐  │
│  │ Primary care visit: [$150] - [$300]                  │  │
│  │ Specialist visit:   [$200] - [$500]                  │  │
│  │ ...                                                  │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─── Results (shown after simulation) ─────────────────┐  │
│  │                                                       │  │
│  │  Share this scenario: [https://caca.app/a3f8...] 📋  │  │
│  │                                                       │  │
│  │  Rankings table...                                   │  │
│  │  Histograms...                                       │  │
│  │  Breakdown per plan...                               │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Key interactions:**

- "Based on" dropdown loads a starter profile, user can customize
- "Add detailed entry" expands a service to probability/count/scheduled fields
- Plans list populated from `plans/` directory
- Costs section collapsed by default (power users can tweak)
- Results appear after running, with shareable URL

## Client-Side State (Alpine.js)

```javascript
Alpine.data('simulator', () => ({
  people: [
    {
      name: 'Person 1',
      baseProfile: 'healthy-young-adult',
      services: {
        primary_care_visit: { type: 'simple', count: 3 },
        emergency_room: {
          type: 'detailed',
          entries: [{ probability: 0.1, count: 1 }]
        }
      }
    }
  ],
  selectedPlans: ['bs-bronze-60-hdhp-ppo', 'bs-silver-70-trio-hmo'],
  costs: { /* loaded from server defaults */ },
  results: null,
  loading: false,

  async run() {
    this.loading = true
    const response = await fetch('/run', {
      method: 'POST',
      body: JSON.stringify({
        people: this.people,
        plans: this.selectedPlans,
        costs: this.costs
      })
    })
    const data = await response.json()
    this.results = data.results
    history.pushState({}, '', '/' + data.hash)
    this.loading = false
  }
}))
```

**Server provides on page load:**

```html
<script>
  window.CACA_DATA = {
    availablePlans: {{ plans | tojson }},
    availableProfiles: {{ profiles | tojson }},
    defaultCosts: {{ costs | tojson }},
    session: {{ session | tojson }}  // null on /, populated on /{hash}
  }
</script>
```

## File Structure

```
caca/
  web/
    __init__.py
    app.py              # FastAPI app, routes
    sessions.py         # SessionStore abstraction + FileSessionStore
    templates/
      index.html        # Single page with Alpine.js
    static/
      style.css         # Tailwind (CDN or compiled)
      app.js            # Alpine components (if separate from HTML)
```

## CLI Integration

New subcommand:

```bash
caca serve              # Start web server
caca serve --port 8080  # Custom port
```

## Dependencies

Add to `pyproject.toml`:

```toml
dependencies = [
    ...
    "fastapi>=0.100",
    "uvicorn>=0.20",
    "jinja2>=3.0",
]
```

## Error Handling

**Validation errors (on /run):**

- 400 with `{error: "Missing name for person 2"}`
- Alpine displays error message above results area

**Invalid hash (on /{hash}):**

- 404 page with "Scenario not found" + link to start fresh
- Hash validated as hex with correct length (prevents path traversal)

**Simulation errors:**

- 500 with `{error: "Simulation failed: ..."}`

**Server overload:**

- 503 Service Unavailable with `Retry-After` header
- When concurrent simulations exceed limit

**Hash validation (security):**

```python
import re

def is_valid_hash(h: str) -> bool:
    return bool(re.match(r'^[a-f0-9]{16,64}$', h))
```

## Rate Limiting

```python
import asyncio

class SimulationLimiter:
    def __init__(self, max_concurrent: int = 4, max_queued: int = 10):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.queued = 0
        self.max_queued = max_queued

    async def acquire(self):
        if self.queued >= self.max_queued:
            raise TooManyRequestsError()
        self.queued += 1
        await self.semaphore.acquire()
        self.queued -= 1

    def release(self):
        self.semaphore.release()
```

**Response on overload:**

```python
return JSONResponse(
    status_code=503,
    content={"error": "Server busy, please try again shortly"},
    headers={"Retry-After": "5"}
)
```

## UI States

- **Loading** → "Run Simulation" button shows spinner, disabled
- **Error** → Red banner above results with message
- **Success** → Results appear, URL updates, share link shown
- **Busy (503)** → "Server is busy, please wait..." with retry button
