# PURPOSE: Build and run commands for Care Casino

.PHONY: help deps test validate clean

help:
	@echo "Care Casino - Monte Carlo healthcare cost simulator"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  help      Show this help message (default)"
	@echo "  deps      Create venv and install dependencies"
	@echo "  test      Run test suite (includes validation)"
	@echo "  validate  Validate plan/profile/cost files"
	@echo "  clean     Remove cache and compiled files"

deps:
	python -m venv .venv
	.venv/bin/pip install -e ".[dev]"

test: validate
	.venv/bin/pytest

validate:
	.venv/bin/caca validate plans/ profiles/ costs/

clean:
	rm -rf .caca-cache/
	rm -rf __pycache__/
	rm -rf .pytest_cache/
	find . -name "*.pyc" -delete
