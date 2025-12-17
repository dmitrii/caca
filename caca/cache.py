# PURPOSE: Cache simulation results with code-aware invalidation

import hashlib
import json
from pathlib import Path
from typing import Any

# Files that affect calculation results
CALC_FILES = [
    "caca/plan_calculator.py",
    "caca/models.py",
    "caca/simulation_runner.py",
    "caca/event_generator.py",
]


def compute_inputs_hash(inputs: dict) -> str:
    """Compute a hash of the canonical inputs."""
    # Sort keys for deterministic output
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def get_code_hash() -> str:
    """Compute a hash of the calculation-affecting source files."""
    hasher = hashlib.sha256()

    # Find the package root
    package_root = Path(__file__).parent.parent

    for rel_path in CALC_FILES:
        file_path = package_root / rel_path
        if file_path.exists():
            hasher.update(file_path.read_bytes())

    return hasher.hexdigest()[:16]


def compute_cache_key(inputs: dict) -> str:
    """Compute the full cache key from inputs and code."""
    inputs_hash = compute_inputs_hash(inputs)
    code_hash = get_code_hash()
    return f"{inputs_hash}_{code_hash}"


class CacheManager:
    """Manage disk-based cache for simulation results."""

    def __init__(self, cache_dir: Path | str):
        self.cache_dir = Path(cache_dir)

    def get(self, key: str) -> dict | None:
        """Get cached results by key."""
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            return None
        with open(cache_file) as f:
            return json.load(f)

    def set(self, key: str, data: dict) -> None:
        """Store results in cache."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = self.cache_dir / f"{key}.json"
        with open(cache_file, "w") as f:
            json.dump(data, f)

    def has(self, key: str) -> bool:
        """Check if key exists in cache."""
        cache_file = self.cache_dir / f"{key}.json"
        return cache_file.exists()
