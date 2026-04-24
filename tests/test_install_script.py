"""Tests for scripts/install.sh"""

import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"


def _source_and_run(commands):
    """Source install.sh with main() suppressed, then run the given commands."""
    full_cmd = f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; {commands}'
    return subprocess.run(["sh", "-c", full_cmd], capture_output=True, text=True, timeout=30)


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

    def test_default_install_dir_is_user_local_bin(self):
        content = INSTALL_SCRIPT.read_text()
        assert '${INSTALL_DIR:-$HOME/.local/bin}' in content


class TestInstallDetectOS:
    """Test detect_os function by sourcing the script in a subshell."""

    def _run_function(self, function_name):
        """Source the script and call a function, suppressing main()."""
        result = subprocess.run(
            ["sh", "-c", f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; {function_name}'],
            capture_output=True,
            text=True,
            timeout=30,
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

    @staticmethod
    def _compute_sha256(path):
        """Platform-aware SHA256 computation (sha256sum on Linux, shasum on macOS)."""
        if shutil.which("sha256sum"):
            r = subprocess.run(["sha256sum", str(path)], capture_output=True, text=True)
        else:
            r = subprocess.run(["shasum", "-a", "256", str(path)], capture_output=True, text=True)
        return r.stdout.strip()

    def test_checksum_passes_for_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")

            # Generate correct checksum
            checksum = self._compute_sha256(test_file)

            # Write checksum file
            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text(checksum)

            # Run verify_checksum
            result = _source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
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
            result = _source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert result.returncode != 0, "Checksum verification should fail for tampered file"

    def test_checksum_fails_when_no_sha256_tool(self):
        """verify_checksum must hard-fail (not skip) when no sha256 tool is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")
            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text("abc123  test.tar.gz")

            # Hide sha256sum and shasum by using a PATH with no real tools
            full_cmd = (
                f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; '
                f'PATH=/nonexistent verify_checksum "{tmpdir}" "test.tar.gz"'
            )
            result = subprocess.run(["sh", "-c", full_cmd], capture_output=True, text=True, timeout=30)
            assert result.returncode != 0, "verify_checksum must fail when no sha256 tool is available"

    def test_checksum_fails_when_checksum_file_empty(self):
        """verify_checksum must fail when the .sha256 file is empty."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")
            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text("")

            result = _source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert result.returncode != 0, "verify_checksum must fail when checksum file is empty"

    def test_checksum_error_message_on_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.tar.gz"
            test_file.write_text("hello world")

            checksum_file = Path(tmpdir) / "test.tar.gz.sha256"
            checksum_file.write_text("badchecksum  test.tar.gz")

            result = _source_and_run(f'verify_checksum "{tmpdir}" "test.tar.gz"')
            assert result.returncode != 0, "verify_checksum should exit non-zero on mismatch"
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

    def test_mv_source_uses_platform_qualified_name(self):
        """After extraction, the binary is named mytruv-{os}-{arch}, not mytruv.
        The mv command must reference the ${extracted} variable."""
        content = INSTALL_SCRIPT.read_text()

        # Find all mv lines in the script
        mv_lines = [line.strip() for line in content.splitlines() if line.strip().startswith("mv ") or "mv " in line]
        # At least one mv line should reference the ${extracted} variable
        has_extracted_ref = any("${extracted}" in line or "$extracted" in line for line in mv_lines)
        assert has_extracted_ref, (
            f"mv commands must reference ${{extracted}} (platform-qualified name). mv lines: {mv_lines}"
        )

    def test_chmod_uses_sudo_when_needed(self):
        """chmod +x must use sudo when the install dir is not writable."""
        content = INSTALL_SCRIPT.read_text()
        assert "sudo chmod" in content, "chmod must use sudo on the sudo path, since the file is owned by root"

    def test_install_dir_overridable(self):
        """INSTALL_DIR should be overridable via environment variable."""
        content = INSTALL_SCRIPT.read_text()
        assert "${INSTALL_DIR:-" in content, (
            "INSTALL_DIR should use ${INSTALL_DIR:-/usr/local/bin} for env var override"
        )

    def test_mytruv_version_overridable(self):
        """MYTRUV_VERSION should bypass the API call."""
        content = INSTALL_SCRIPT.read_text()
        assert "MYTRUV_VERSION" in content

    def test_github_token_supported(self):
        """GITHUB_TOKEN should be passed to the API call."""
        content = INSTALL_SCRIPT.read_text()
        assert "GITHUB_TOKEN" in content

    def test_version_format_validated(self):
        """Version string must be validated before use."""
        content = INSTALL_SCRIPT.read_text()
        assert "v[0-9]" in content, "Version string must be validated to match semver-like pattern"

    def test_version_regex_accepts_expected_tags(self):
        """The version regex must accept stable releases and -rc.N pre-releases, reject malformed tags."""
        import re

        content = INSTALL_SCRIPT.read_text()
        m = re.search(r"grep -Eq\s*'(\^[^']+\$)'", content)
        assert m, "Could not locate version-check regex in install.sh"
        regex = re.compile(m.group(1))

        for valid in ("v0.1.0", "v1.2.3", "v10.20.30", "v0.1.0-rc.1", "v1.0.0-beta.2", "v2.0.0-alpha"):
            assert regex.match(valid), f"regex should accept {valid!r}"
        for invalid in ("v0.1", "1.2.3", "v0.1.0-", "v0.1.0-rc_1", "v0.1.0+build", ""):
            assert not regex.match(invalid), f"regex should reject {invalid!r}"

    def test_tar_extracts_only_expected_binary(self):
        """tar must extract only the expected binary, not all archive entries."""
        content = INSTALL_SCRIPT.read_text()
        # Find the tar extraction line
        tar_lines = [line.strip() for line in content.splitlines() if "tar -xzf" in line]
        assert any("${extracted}" in line or "$extracted" in line for line in tar_lines), (
            f"tar must extract only the named binary. tar lines: {tar_lines}"
        )


class TestInstallFailurePaths:
    """Test failure branches in install.sh."""

    def test_unsupported_os_aborts(self):
        """install.sh must abort when detect_os returns empty string."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; detect_os() {{ echo ""; }}; main',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0, "install.sh must exit non-zero for unsupported OS"
        assert "unsupported platform" in result.stderr.lower()

    def test_unsupported_arch_aborts(self):
        """install.sh must abort when detect_arch returns empty string."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; detect_arch() {{ echo ""; }}; main',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0, "install.sh must exit non-zero for unsupported arch"
        assert "unsupported platform" in result.stderr.lower()

    def test_empty_version_aborts(self):
        """install.sh must abort when get_latest_version returns empty."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; get_latest_version() {{ echo ""; }}; main',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0, "install.sh must exit non-zero for empty version"
        assert "could not determine" in result.stderr.lower()

    def test_invalid_version_format_aborts(self):
        """install.sh must abort when version doesn't match v[0-9]* pattern."""
        result = subprocess.run(
            [
                "sh",
                "-c",
                f'eval "$(sed "/^main$/d" "{INSTALL_SCRIPT}")"; get_latest_version() {{ echo "not-a-version"; }}; main',
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode != 0, "install.sh must exit non-zero for invalid version format"
        assert "unexpected version" in result.stderr.lower()
