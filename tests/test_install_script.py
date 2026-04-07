"""Tests for scripts/install.sh"""

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"


class TestInstallScriptExists:
    def test_script_exists(self):
        assert INSTALL_SCRIPT.exists()

    def test_script_is_executable(self):
        mode = INSTALL_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "install.sh should be executable"

    def test_script_starts_with_shebang(self):
        content = INSTALL_SCRIPT.read_text()
        assert content.startswith("#!/bin/sh"), "install.sh should use #!/bin/sh shebang"

    def test_script_uses_set_e(self):
        content = INSTALL_SCRIPT.read_text()
        assert "set -e" in content, "install.sh should use set -e for fail-fast"


class TestInstallScriptConfig:
    def test_repo_url_points_to_truvhq(self):
        content = INSTALL_SCRIPT.read_text()
        assert "truvhq/mytruv-cli" in content

    def test_binary_name_is_mytruv(self):
        content = INSTALL_SCRIPT.read_text()
        assert 'BINARY_NAME="mytruv"' in content or "BINARY_NAME='mytruv'" in content

    def test_installs_to_usr_local_bin(self):
        content = INSTALL_SCRIPT.read_text()
        assert "/usr/local/bin" in content


class TestInstallDetectOS:
    """Test detect_os function by sourcing the script in a subshell."""

    def _run_function(self, function_name):
        """Source the script and call a function, suppressing main()."""
        result = subprocess.run(
            ["sh", "-c", f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; {function_name}'],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_detect_os_returns_nonempty(self):
        result = self._run_function("detect_os")
        assert result in ("darwin", "linux"), f"detect_os returned unexpected value: '{result}'"

    def test_detect_arch_returns_nonempty(self):
        result = self._run_function("detect_arch")
        assert result in ("amd64", "arm64"), f"detect_arch returned unexpected value: '{result}'"


class TestInstallChecksumVerification:
    """Test verify_checksum function with real files."""

    def _source_and_run(self, commands):
        full_cmd = f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; {commands}'
        return subprocess.run(["sh", "-c", full_cmd], capture_output=True, text=True)

    def test_checksum_passes_for_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")

            # Generate correct checksum
            result = subprocess.run(
                ["shasum", "-a", "256", str(test_file)], capture_output=True, text=True
            )
            checksum = result.stdout.strip()

            # Write checksum file
            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text(checksum)

            # Run verify_checksum
            result = self._source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert result.returncode == 0, f"Checksum verification should pass: {result.stderr}"

    def test_checksum_fails_for_tampered_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")

            # Write wrong checksum
            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text("0000000000000000000000000000000000000000000000000000000000000000  test.tar.gz")

            # Run verify_checksum — should fail
            result = self._source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert result.returncode != 0, "Checksum verification should fail for tampered file"

    def test_checksum_error_message_on_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")

            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text("badchecksum  test.tar.gz")

            result = self._source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert "checksum mismatch" in result.stderr.lower()


class TestInstallScriptFlow:
    """Test the overall script structure has required steps."""

    def test_script_downloads_binary(self):
        content = INSTALL_SCRIPT.read_text()
        assert "curl" in content, "Script should use curl to download"

    def test_script_verifies_checksum(self):
        content = INSTALL_SCRIPT.read_text()
        assert "verify_checksum" in content or "sha256" in content

    def test_script_extracts_archive(self):
        content = INSTALL_SCRIPT.read_text()
        assert "tar" in content, "Script should extract tar archive"

    def test_script_handles_permissions(self):
        """Script should use sudo if /usr/local/bin is not writable."""
        content = INSTALL_SCRIPT.read_text()
        assert "sudo" in content

    def test_script_cleans_up_tempdir(self):
        content = INSTALL_SCRIPT.read_text()
        assert "mktemp" in content and "trap" in content, "Script should create and clean up temp dir"

    def test_script_prints_success_message(self):
        content = INSTALL_SCRIPT.read_text()
        assert "installed successfully" in content.lower() or "success" in content.lower()

    def test_script_uses_github_releases_url(self):
        content = INSTALL_SCRIPT.read_text()
        assert "github.com" in content and "/releases/" in content
