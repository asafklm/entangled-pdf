"""CLI integration tests for entangle-pdf command.

These tests verify the installed CLI entry point works correctly,
including the correct command name in help output.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


class TestCLIEntryPoint:
    """Tests for the installed entangle-pdf CLI entry point."""

    def test_entry_point_script_exists(self):
        """Verify the entangle-pdf entry point script is installed in bin/."""
        # Find the script in the virtual environment's bin directory
        venv_bin = Path(sys.executable).parent
        entry_point = venv_bin / "entangle-pdf"

        assert entry_point.exists(), \
            f"Entry point script not found: {entry_point}"
        assert entry_point.is_file(), \
            f"Entry point is not a file: {entry_point}"

    def test_entry_point_is_executable(self):
        """Verify the entangle-pdf entry point is executable."""
        venv_bin = Path(sys.executable).parent
        entry_point = venv_bin / "entangle-pdf"

        if not entry_point.exists():
            pytest.skip(f"Entry point not found: {entry_point}")

        # Check file is executable
        assert entry_point.stat().st_mode & 0o111, \
            f"Entry point is not executable: {entry_point}"

    def test_entry_point_imports_correct_module(self):
        """Verify the entry point script imports from entangledpdf package."""
        venv_bin = Path(sys.executable).parent
        entry_point = venv_bin / "entangle-pdf"

        if not entry_point.exists():
            pytest.skip(f"Entry point not found: {entry_point}")

        content = entry_point.read_text()
        assert "from entangledpdf.cli import main" in content, \
            "Entry point does not import from entangledpdf package"
        assert "pdfserver" not in content, \
            "Entry point still references old pdfserver package"


class TestCLIHelpOutput:
    """Tests for CLI help output showing correct command name."""

    def test_main_help_shows_correct_program_name(self):
        """Verify --help shows 'usage: entangle-pdf' not old name."""
        env = {"PDF_SERVER_API_KEY": "test-key"}

        result = subprocess.run(
            ["entangle-pdf", "--help"],
            capture_output=True,
            text=True,
            env={**env, **dict(os.environ)},
        )

        # Command should succeed
        assert result.returncode == 0, \
            f"entangle-pdf --help failed: {result.stderr}"

        # Check usage line shows correct program name
        assert "usage: entangle-pdf" in result.stdout, \
            f"Help shows wrong program name. Output:\n{result.stdout}"

        # Verify old name is NOT present
        assert "usage: pdf-server" not in result.stdout, \
            f"Help still shows old pdf-server name. Output:\n{result.stdout}"

    def test_start_subcommand_help_shows_correct_name(self):
        """Verify start --help shows correct program name."""
        result = subprocess.run(
            ["entangle-pdf", "start", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, \
            f"entangle-pdf start --help failed: {result.stderr}"

        # Check usage line shows correct program name with subcommand
        assert "usage: entangle-pdf start" in result.stdout, \
            f"Start help shows wrong program name. Output:\n{result.stdout}"

    def test_sync_subcommand_help_shows_correct_name(self):
        """Verify sync --help shows correct program name."""
        result = subprocess.run(
            ["entangle-pdf", "sync", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, \
            f"entangle-pdf sync --help failed: {result.stderr}"

        # Check usage line shows correct program name with subcommand
        assert "usage: entangle-pdf sync" in result.stdout, \
            f"Sync help shows wrong program name. Output:\n{result.stdout}"

    def test_status_subcommand_help_shows_correct_name(self):
        """Verify status --help shows correct program name."""
        result = subprocess.run(
            ["entangle-pdf", "status", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, \
            f"entangle-pdf status --help failed: {result.stderr}"

        # Check usage line shows correct program name with subcommand
        assert "usage: entangle-pdf status" in result.stdout, \
            f"Status help shows wrong program name. Output:\n{result.stdout}"


class TestCLISubcommands:
    """Tests for CLI subcommands functionality."""

    def test_status_command_runs(self):
        """Verify entangle-pdf status command executes."""
        result = subprocess.run(
            ["entangle-pdf", "status"],
            capture_output=True,
            text=True,
        )

        # Should return 0 (no server) or 0 (server running)
        assert result.returncode == 0, \
            f"entangle-pdf status failed: {result.stderr}"

        # Output should mention server status
        assert "not running" in result.stdout.lower() or \
               "running" in result.stdout.lower() or \
               "port" in result.stdout.lower(), \
            f"Unexpected status output: {result.stdout}"

    def test_sync_requires_pdf_argument(self):
        """Verify entangle-pdf sync requires PDF file argument."""
        env = {"PDF_SERVER_API_KEY": "test-key"}

        result = subprocess.run(
            ["entangle-pdf", "sync"],
            capture_output=True,
            text=True,
            env={**env, **dict(os.environ)},
        )

        # Should fail without PDF file
        assert result.returncode != 0, \
            "sync command should require PDF argument"

        # Error should mention required argument
        assert "pdf_file" in result.stderr.lower() or \
               "required" in result.stderr.lower() or \
               "arguments" in result.stderr.lower(), \
            f"Unexpected error message: {result.stderr}"

    def test_start_without_api_key_fails(self):
        """Verify entangle-pdf start fails without API key."""
        # Clear API key from environment
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("PDF_SERVER")}

        result = subprocess.run(
            ["entangle-pdf", "start", "--http"],
            capture_output=True,
            text=True,
            env=env,
            timeout=5,
        )

        # Should fail without API key
        assert result.returncode != 0, \
            "start should fail without API key"

        # Error should mention API key
        assert "api" in result.stderr.lower() or \
               "api-key" in result.stderr.lower() or \
               "pdf_server_api_key" in result.stderr.lower(), \
            f"Error should mention API key requirement: {result.stderr}"

    def test_help_includes_description(self):
        """Verify help includes EntangledPdf description."""
        env = {"PDF_SERVER_API_KEY": "test-key"}

        result = subprocess.run(
            ["entangle-pdf", "--help"],
            capture_output=True,
            text=True,
            env={**env, **dict(os.environ)},
        )

        assert result.returncode == 0, \
            f"--help failed: {result.stderr}"

        # Should mention EntangledPdf
        assert "entangledpdf" in result.stdout.lower() or \
               "pdf server" in result.stdout.lower(), \
            f"Help should describe the tool. Output:\n{result.stdout}"


class TestCLIOldCommandNotPresent:
    """Tests verifying old pdf-server command no longer exists."""

    def test_old_pdf_server_command_not_found(self):
        """Verify old pdf-server command is no longer available."""
        try:
            result = subprocess.run(
                ["pdf-server", "--help"],
                capture_output=True,
                text=True,
            )
            # If we get here, command exists - that's unexpected
            pytest.fail(f"Old pdf-server command should not exist, but it ran with output: {result.stdout}")
        except FileNotFoundError:
            # This is expected - command doesn't exist
            pass
        except OSError as e:
            # Other OS errors also acceptable (command not found)
            assert "no such file" in str(e).lower() or \
                   "not found" in str(e).lower(), \
                f"Unexpected error: {e}"


class TestCLISubcommandList:
    """Tests for available subcommands."""

    def test_main_help_lists_all_subcommands(self):
        """Verify main help lists start, status, sync subcommands."""
        env = {"PDF_SERVER_API_KEY": "test-key"}

        result = subprocess.run(
            ["entangle-pdf", "--help"],
            capture_output=True,
            text=True,
            env={**env, **dict(os.environ)},
        )

        assert result.returncode == 0, \
            f"--help failed: {result.stderr}"

        help_text = result.stdout.lower()

        # Check all subcommands are listed
        assert "start" in help_text, "Help should list 'start' subcommand"
        assert "status" in help_text, "Help should list 'status' subcommand"
        assert "sync" in help_text, "Help should list 'sync' subcommand"
