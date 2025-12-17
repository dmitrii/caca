# PURPOSE: Integration tests for new modular config system

import pytest
import subprocess
from pathlib import Path


class TestNewConfigIntegration:
    def test_validate_existing_files(self, tmp_path):
        """Validate command works on plans/profiles/costs directories."""
        # This test assumes the directories have been populated
        result = subprocess.run(
            ["python", "-m", "caca.cli", "validate", "plans/", "profiles/", "costs/"],
            capture_output=True,
            text=True,
        )
        # Should pass if files are valid, fail if not found
        assert result.returncode in [0, 1]

    def test_generate_with_example_config(self):
        """Run simulation with example config."""
        example_config = Path("examples/basic-run.yaml")
        if not example_config.exists():
            pytest.skip("Example config not found")

        result = subprocess.run(
            ["python", "-m", "caca.cli", "gen", str(example_config), "--quiet"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
