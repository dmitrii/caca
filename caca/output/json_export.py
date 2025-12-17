# PURPOSE: JSON export for simulation results

import json
from typing import TextIO
from caca.results import ResultsStore


class JsonExporter:
    """Exports simulation results to JSON."""

    def export(
        self,
        output: TextIO,
        store: ResultsStore,
        summary: dict[str, dict],
    ) -> None:
        """Export results to JSON."""
        data = store.to_json()
        data["summary"] = summary

        json.dump(data, output, indent=2)
