# PURPOSE: Build and run commands for Care Casino

.PHONY: help test install run

help:
	@echo "Care Casino - Monte Carlo healthcare cost simulator"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help     Show this help message (default)"
	@echo "  test     Run test suite"
	@echo "  install  Install package in development mode"
	@echo "  run      Run simulation with config.yaml"

test:
	.venv/bin/pytest -v

install:
	.venv/bin/pip install -e .

run:
	.venv/bin/caca config.yaml
