"""Tests for README.md and pyproject.toml packaging config."""

from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).parent.parent
README = REPO_ROOT / "README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"


class TestPyprojectBuildDeps:
    def _get_dev_deps(self):
        config = tomllib.loads(PYPROJECT.read_text())
        return config.get("project", {}).get("optional-dependencies", {}).get("dev", [])

    def test_has_nuitka_dependency(self):
        deps = self._get_dev_deps()
        assert any("nuitka" in d.lower() for d in deps), "pyproject.toml should have nuitka in dev deps"

    def test_has_ordered_set_dependency(self):
        deps = self._get_dev_deps()
        assert any("ordered-set" in d.lower() for d in deps), "pyproject.toml should have ordered-set in dev deps"

    def test_has_pyyaml_dependency(self):
        deps = self._get_dev_deps()
        assert any("pyyaml" in d.lower() for d in deps), (
            "pyyaml should be in [project.optional-dependencies] dev, not [dependency-groups]"
        )

    def test_no_dependency_groups_section(self):
        """All dev deps should be in [project.optional-dependencies], not split across [dependency-groups]."""
        config = tomllib.loads(PYPROJECT.read_text())
        assert "dependency-groups" not in config, (
            "pyproject.toml should not use [dependency-groups] — consolidate into [project.optional-dependencies]"
        )

    def test_has_hatchling_build_backend(self):
        config = tomllib.loads(PYPROJECT.read_text())
        backend = config["build-system"]["build-backend"]
        assert backend == "hatchling.build"


class TestReadmeInstallSection:
    def test_has_curl_install_command(self):
        content = README.read_text()
        assert "curl" in content and "install.sh" in content, "README should have curl | sh install"

    def test_curl_points_to_correct_repo(self):
        content = README.read_text()
        assert "truvhq/mytruv-cli" in content

    def test_has_uv_alternative(self):
        content = README.read_text()
        assert "uv tool install" in content

    def test_uv_install_points_to_github(self):
        content = README.read_text()
        assert "git+https://github.com/truvhq/mytruv-cli" in content


class TestReadmeStructure:
    def test_has_install_section(self):
        content = README.read_text()
        assert "## Install" in content

    def test_has_quick_start_section(self):
        content = README.read_text()
        assert "## Quick Start" in content

    def test_has_commands_section(self):
        content = README.read_text()
        assert "## Commands" in content

    def test_has_agent_automation_section(self):
        content = README.read_text()
        assert "## Agent / Automation Usage" in content

    def test_has_license_section(self):
        content = README.read_text()
        assert "## License" in content


class TestReadmeCommands:
    """Ensure README documents all CLI commands."""

    def test_documents_auth_login(self):
        content = README.read_text()
        assert "auth login" in content

    def test_documents_auth_logout(self):
        content = README.read_text()
        assert "auth logout" in content

    def test_documents_auth_status(self):
        content = README.read_text()
        assert "auth status" in content

    def test_documents_balances(self):
        content = README.read_text()
        assert "balances" in content

    def test_documents_transactions(self):
        content = README.read_text()
        assert "transactions" in content

    def test_documents_spending(self):
        content = README.read_text()
        assert "spending" in content

    def test_documents_income(self):
        content = README.read_text()
        assert "income" in content

    def test_documents_links(self):
        content = README.read_text()
        assert "links" in content

    def test_documents_user(self):
        content = README.read_text()
        assert "user" in content
