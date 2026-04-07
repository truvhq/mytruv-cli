"""Tests for scripts/build.sh"""

import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build.sh"


class TestBuildScriptExists:
    def test_script_exists(self):
        assert BUILD_SCRIPT.exists()

    def test_script_is_executable(self):
        mode = BUILD_SCRIPT.stat().st_mode
        assert mode & stat.S_IXUSR, "build.sh should be executable"

    def test_script_starts_with_shebang(self):
        content = BUILD_SCRIPT.read_text()
        assert content.startswith("#!/bin/sh"), "build.sh should use #!/bin/sh shebang"

    def test_script_uses_set_e(self):
        content = BUILD_SCRIPT.read_text()
        assert "set -e" in content


class TestBuildScriptConfig:
    def test_binary_name_is_mytruv(self):
        content = BUILD_SCRIPT.read_text()
        assert "mytruv" in content

    def test_output_dir_is_dist(self):
        content = BUILD_SCRIPT.read_text()
        assert "dist" in content


class TestBuildDetectPlatform:
    """Test detect_os and detect_arch functions."""

    def _run_function(self, function_name):
        """Source only the functions from the script (skip execution lines)."""
        # Extract function definitions and call them
        result = subprocess.run(
            [
                "sh",
                "-c",
                f"""
                detect_os() {{
                    $(sed -n '/^detect_os()/,/^}}/p' "{BUILD_SCRIPT}" | tail -n +2)
                }}
                detect_arch() {{
                    $(sed -n '/^detect_arch()/,/^}}/p' "{BUILD_SCRIPT}" | tail -n +2)
                }}
                # Source the actual functions from the script
                eval "$(grep -A 20 '^detect_os()' "{BUILD_SCRIPT}" | head -7)"
                eval "$(grep -A 20 '^detect_arch()' "{BUILD_SCRIPT}" | head -7)"
                {function_name}
                """,
            ],
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def test_detect_os_returns_valid_platform(self):
        result = self._run_function("detect_os")
        assert result in ("darwin", "linux"), f"detect_os returned unexpected: '{result}'"

    def test_detect_arch_returns_valid_arch(self):
        result = self._run_function("detect_arch")
        assert result in ("amd64", "arm64"), f"detect_arch returned unexpected: '{result}'"


class TestBuildScriptUsesNuitka:
    def test_uses_nuitka(self):
        content = BUILD_SCRIPT.read_text()
        assert "nuitka" in content.lower(), "build.sh should use Nuitka for compilation"

    def test_uses_standalone_flag(self):
        content = BUILD_SCRIPT.read_text()
        assert "--standalone" in content or "--onefile" in content

    def test_includes_mytruv_cli_package(self):
        content = BUILD_SCRIPT.read_text()
        assert "mytruv_cli" in content

    def test_targets_main_entry_point(self):
        content = BUILD_SCRIPT.read_text()
        assert "src/mytruv_cli/main.py" in content


class TestBuildScriptOutputNaming:
    def test_output_name_includes_os_and_arch(self):
        """Binary name should follow pattern: mytruv-{os}-{arch}"""
        content = BUILD_SCRIPT.read_text()
        # Script should compose output name from OS and ARCH variables
        assert "OS" in content and "ARCH" in content
        # And combine them into the output name
        assert "${OS}" in content or "$OS" in content
        assert "${ARCH}" in content or "$ARCH" in content

    def test_runs_smoke_test(self):
        content = BUILD_SCRIPT.read_text()
        assert "--help" in content, "build.sh should run a smoke test with --help"


class TestBuildScriptSmokeTestFatal:
    def test_smoke_test_failure_is_fatal(self):
        """If the smoke test fails, build.sh must exit non-zero."""
        content = BUILD_SCRIPT.read_text()
        # The script must NOT use the pattern: cmd && echo ok || echo fail
        # because || suppresses the exit code under set -e
        assert '|| echo "Smoke test failed!"' not in content, (
            "Smoke test uses || fallback which suppresses non-zero exit under set -e"
        )


class TestBuildScriptUnknownPlatformGuard:
    def test_unknown_os_aborts(self):
        """build.sh must abort when detect_os returns 'unknown'."""
        content = BUILD_SCRIPT.read_text()
        assert '"unknown"' in content or "'unknown'" in content
        # Must have a guard that checks for unknown and exits
        assert "unknown" in content and "exit 1" in content, (
            "build.sh must guard against unknown OS/ARCH and exit 1"
        )


class TestBuildScriptQuoting:
    def test_smoke_test_path_is_quoted(self):
        """The binary path in the smoke test must be quoted."""
        content = BUILD_SCRIPT.read_text()
        assert '"./dist/${OUTPUT_NAME}"' in content or '"./dist/$OUTPUT_NAME"' in content, (
            "Binary path in smoke test must be double-quoted"
        )
