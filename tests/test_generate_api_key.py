"""Tests for the generate-api-key CLI subcommand.

This file contains unit tests that call the internal function directly,
as well as integration tests that exercise the CLI via the subprocess
invocation pattern used elsewhere in the repository.
"""

import re
import subprocess
import sys
from types import SimpleNamespace
from pathlib import Path
from typing import Iterable

import pytest

from entangledpdf.cli import cmd_generate_api_key


def get_cli_path() -> Path:
    """Helper to locate the entangle-pdf CLI executable in the current venv."""
    return Path(sys.executable).parent / "entangle-pdf"


def _hex_like(key: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", key))


class TestGenerateApiKeyUnit:
    """Unit tests for the cmd_generate_api_key function."""

    def test_basic_key_generation(self, capsys) -> None:
        args = SimpleNamespace(shell=False)
        rc = cmd_generate_api_key(args)  # type: ignore[arg-type]
        assert rc == 0
        out = capsys.readouterr().out.strip()
        assert len(out) == 64
        assert _hex_like(out)

    def test_key_uniqueness(self, capsys) -> None:
        args = SimpleNamespace(shell=False)
        cmd_generate_api_key(args)  # first key
        first = capsys.readouterr().out.strip()
        cmd_generate_api_key(args)  # second key
        second = capsys.readouterr().out.strip()
        assert first != second, "Consecutive API keys should be unique"
        assert _hex_like(first) and _hex_like(second)

    def test_shell_output_format(self, capsys) -> None:
        args = SimpleNamespace(shell=True)
        rc = cmd_generate_api_key(args)  # type: ignore[arg-type]
        assert rc == 0
        captured = capsys.readouterr()
        out = captured.out.strip().splitlines()
        assert len(out) >= 1
        shell_line = out[0]
        m = re.match(r'^export ENTANGLEDPDF_API_KEY="([0-9a-f]{64})"$', shell_line)
        assert m is not None, f"Shell output not in expected format: {shell_line}"
        # Capture stderr messages from the same read
        err_lines = captured.err.strip().splitlines()
        assert len(err_lines) >= 2
        assert any("Add the above line" in line for line in err_lines)
        assert any("source ~/.bashrc" in line for line in err_lines)

    def test_shell_output_contains_comments_in_stderr(self, capsys) -> None:
        # Ensure the stderr contains the helper messages even when only checking
        # the first couple of lines above.
        args = SimpleNamespace(shell=True)
        cmd_generate_api_key(args)  # type: ignore[arg-type]
        _ = capsys.readouterr()  # capture and reset
        # Run again to verify the stderr messages are present
        cmd_generate_api_key(args)  # type: ignore[arg-type]
        captured = capsys.readouterr()
        assert any("Add the above line" in line for line in captured.err.splitlines())


class TestGenerateApiKeyIntegration:
    """Integration tests using subprocess, mirroring existing CLI tests."""

    def test_help_shows_generate_api_key(self) -> None:
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "generate-api-key" in result.stdout

    def test_generate_api_key_runs_without_shell(self) -> None:
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        stdout = result.stdout.strip()
        assert len(stdout) == 64
        assert _hex_like(stdout)

    def test_generate_api_key_runs_with_shell_output(self) -> None:
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key", "--shell"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        stdout = result.stdout.strip().splitlines()
        assert len(stdout) >= 1
        m = re.match(r'^export ENTANGLEDPDF_API_KEY="([0-9a-f]{64})"$', stdout[0])
        assert m is not None
        # stderr should contain helper comments
        err = result.stderr.strip().splitlines()
        assert any("Add the above line" in line for line in err)


class TestGenerateApiKeySecurity:
    """Security-oriented tests for the output format and entropy."""

    def test_entropy_bits_and_format(self) -> None:
        # Generate a batch of keys and verify hex encoding and entropy properties
        keys: list[str] = []
        for _ in range(20):
            args = SimpleNamespace(shell=False)
            # Capture stdout by invoking the function directly
            import io
            from contextlib import redirect_stdout
            buf = io.StringIO()
            with redirect_stdout(buf):
                cmd_generate_api_key(args)  # type: ignore[arg-type]
            key = buf.getvalue().strip()
            keys.append(key)
        # All keys should be 64 hex chars and hex-encoded
        for k in keys:
            assert len(k) == 64
            assert _hex_like(k)
        # Entropy approximation: high likelihood of uniqueness across 20 samples
        assert len(set(keys)) >= 19
