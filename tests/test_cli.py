# PURPOSE: Tests for CLI argument parsing

import pytest
from caca.cli import parse_args


class TestParseArgs:
    def test_generate_subcommand(self):
        args = parse_args(["generate", "config.yaml"])
        assert args.command == "generate"
        assert args.config == "config.yaml"

    def test_gen_alias(self):
        args = parse_args(["gen", "config.yaml"])
        assert args.command == "generate"
        assert args.config == "config.yaml"

    def test_validate_subcommand(self):
        args = parse_args(["validate", "plans/", "costs/"])
        assert args.command == "validate"
        assert args.paths == ["plans/", "costs/"]

    def test_val_alias(self):
        args = parse_args(["val", "plans/"])
        assert args.command == "validate"

    def test_generate_with_breakdown(self):
        args = parse_args(["gen", "config.yaml", "--breakdown", "output.txt"])
        assert args.command == "generate"
        assert args.breakdown == "output.txt"

    def test_generate_with_cache_options(self):
        args = parse_args(["gen", "config.yaml", "--no-cache", "--cache-dir", "/tmp/cache"])
        assert args.no_cache is True
        assert args.cache_dir == "/tmp/cache"


def test_gross_flag_parses():
    from caca.cli import parse_args
    args = parse_args(["generate", "run.yaml", "--gross"])
    assert args.gross is True

def test_gross_defaults_false():
    from caca.cli import parse_args
    args = parse_args(["generate", "run.yaml"])
    assert args.gross is False
