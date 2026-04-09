"""Tests for 'entangle-pdf generate-api-key' command.

Tests API key generation functionality including:
- Key format and entropy
- Uniqueness
- Shell export format
"""

import os
import re
import subprocess
import sys

import pytest

from tests.test_cli_integration import get_cli_path


class TestGenerateApiKeyBasic:
    """Test suite for basic API key generation."""
    
    def test_generate_api_key_outputs_hex_string(self):
        """Key is 64-character hex string."""
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, \
            f"generate-api-key failed: {result.stderr}"
        
        key = result.stdout.strip()
        
        # Should be 64-character hex string
        assert len(key) == 64, \
            f"Key should be 64 chars, got {len(key)}: {key}"
        
        # Should only contain hex characters
        assert re.match(r'^[0-9a-f]+$', key), \
            f"Key should be hex, got: {key}"
    
    def test_generate_api_key_unique(self):
        """Multiple runs produce different keys."""
        # Generate first key
        result1 = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
        )
        
        assert result1.returncode == 0
        key1 = result1.stdout.strip()
        
        # Generate second key
        result2 = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
        )
        
        assert result2.returncode == 0
        key2 = result2.stdout.strip()
        
        # Keys should be different
        assert key1 != key2, \
            f"Keys should be unique, but got same key: {key1}"
    
    def test_generate_api_key_entropy(self):
        """Keys have sufficient entropy (not trivially predictable)."""
        # Generate multiple keys
        keys = []
        for _ in range(10):
            result = subprocess.run(
                [str(get_cli_path()), "generate-api-key"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0
            keys.append(result.stdout.strip())
        
        # All keys should be unique
        assert len(set(keys)) == len(keys), \
            f"Generated duplicate keys: {keys}"
        
        # Keys should not have obvious patterns
        # (This is a basic check - not cryptographic analysis)
        for key in keys:
            # No key should be all same character
            assert len(set(key)) > 10, \
                f"Key has low character diversity: {key}"
    
    def test_generate_api_key_does_not_fail(self):
        """Command always succeeds (no external dependencies)."""
        # This should work even without API_KEY set
        env = {k: v for k, v in os.environ.items()
               if not k.startswith("ENTANGLEDPDF")}
        
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
            env=env,
        )
        
        assert result.returncode == 0, \
            f"generate-api-key should not require any env vars: {result.stderr}"


class TestGenerateApiKeyShellFlag:
    """Test suite for --shell flag."""
    
    def test_generate_api_key_shell_flag(self):
        """--shell outputs 'export ENTANGLEDPDF_API_KEY=...' format."""
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key", "--shell"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0, \
            f"generate-api-key --shell failed: {result.stderr}"
        
        output = result.stdout.strip()
        
        # Should start with "export ENTANGLEDPDF_API_KEY="
        assert output.startswith("export ENTANGLEDPDF_API_KEY="), \
            f"Shell output should start with 'export ENTANGLEDPDF_API_KEY=', got: {output}"
        
        # Extract key value
        key = output.split("=", 1)[1].strip('"')
        
        # Key should be valid hex
        assert len(key) == 64, \
            f"Key in shell output should be 64 chars, got {len(key)}"
        
        assert re.match(r'^[0-9a-f]+$', key), \
            f"Key in shell output should be hex, got: {key}"
    
    def test_generate_api_key_shell_can_be_sourced(self):
        """Shell output can be evaluated by shell."""
        result = subprocess.run(
            [str(get_cli_path()), "generate-api-key", "--shell"],
            capture_output=True,
            text=True,
        )
        
        assert result.returncode == 0
        
        output = result.stdout.strip()
        export_line = output.split("\n")[0]  # Take first line
        
        # Try to evaluate it with bash
        # This verifies the syntax is correct
        test_script = f"""
{export_line}
echo "KEY_SET=$ENTANGLEDPDF_API_KEY"
"""
        
        bash_result = subprocess.run(
            ["bash", "-c", test_script],
            capture_output=True,
            text=True,
        )
        
        # Should succeed
        assert bash_result.returncode == 0, \
            f"Shell output syntax error: {bash_result.stderr}"
        
        # Should show the key was set
        assert "KEY_SET=" in bash_result.stdout, \
            f"Key not set when sourcing: {bash_result.stdout}"


class TestGenerateApiKeyIntegration:
    """Test suite for integration with other commands."""
    
    def test_generated_key_works_with_start(self):
        """Generated key can be used with entangle-pdf start."""
        # Generate a key
        gen_result = subprocess.run(
            [str(get_cli_path()), "generate-api-key"],
            capture_output=True,
            text=True,
        )
        
        assert gen_result.returncode == 0
        key = gen_result.stdout.strip()
        
        # Verify key format
        assert len(key) == 64
        assert re.match(r'^[0-9a-f]+$', key)
        
        # Note: We don't actually test starting with this key here
        # That's covered by the start command tests
        # This test just verifies the generated key format is valid
    
    def test_generated_key_consistency(self):
        """Same command produces valid keys each time."""
        for i in range(5):
            result = subprocess.run(
                [str(get_cli_path()), "generate-api-key"],
                capture_output=True,
                text=True,
            )
            
            assert result.returncode == 0, \
                f"Run {i+1} failed: {result.stderr}"
            
            key = result.stdout.strip()
            
            assert len(key) == 64, \
                f"Run {i+1}: Key wrong length: {key}"
            
            assert re.match(r'^[0-9a-f]+$', key), \
                f"Run {i+1}: Key not hex: {key}"