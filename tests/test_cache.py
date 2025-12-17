# PURPOSE: Tests for caching module

import pytest
import json
import tempfile
from pathlib import Path
from caca.cache import CacheManager, compute_inputs_hash, get_code_hash


class TestComputeInputsHash:
    def test_same_inputs_same_hash(self):
        inputs1 = {"plans": [{"name": "A"}], "people": [{"name": "alice"}]}
        inputs2 = {"plans": [{"name": "A"}], "people": [{"name": "alice"}]}
        assert compute_inputs_hash(inputs1) == compute_inputs_hash(inputs2)

    def test_different_inputs_different_hash(self):
        inputs1 = {"plans": [{"name": "A"}]}
        inputs2 = {"plans": [{"name": "B"}]}
        assert compute_inputs_hash(inputs1) != compute_inputs_hash(inputs2)

    def test_order_independent(self):
        inputs1 = {"a": 1, "b": 2}
        inputs2 = {"b": 2, "a": 1}
        assert compute_inputs_hash(inputs1) == compute_inputs_hash(inputs2)


class TestCodeHash:
    def test_code_hash_is_stable(self):
        hash1 = get_code_hash()
        hash2 = get_code_hash()
        assert hash1 == hash2


class TestCacheManager:
    def test_cache_miss_returns_none(self, tmp_path):
        cache = CacheManager(tmp_path)
        result = cache.get("nonexistent_key")
        assert result is None

    def test_cache_hit_returns_data(self, tmp_path):
        cache = CacheManager(tmp_path)
        data = {"results": [1, 2, 3]}
        cache.set("test_key", data)
        result = cache.get("test_key")
        assert result == data

    def test_cache_creates_directory(self, tmp_path):
        cache_dir = tmp_path / "new_cache"
        cache = CacheManager(cache_dir)
        cache.set("key", {"data": "value"})
        assert cache_dir.exists()
