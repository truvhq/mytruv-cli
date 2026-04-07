"""Tests for .github/workflows/build-binaries.yml"""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).parent.parent
WORKFLOW_FILE = REPO_ROOT / ".github" / "workflows" / "build-binaries.yml"


@pytest.fixture
def workflow():
    assert WORKFLOW_FILE.exists(), "build-binaries.yml should exist"
    data = yaml.safe_load(WORKFLOW_FILE.read_text())
    # PyYAML parses "on:" as boolean True — normalize it
    if True in data:
        data["on"] = data.pop(True)
    return data


class TestWorkflowTrigger:
    def test_triggers_on_version_tags(self, workflow):
        tags = workflow["on"]["push"]["tags"]
        assert "v*" in tags, "Workflow should trigger on v* tags"

    def test_does_not_trigger_on_branches(self, workflow):
        push_config = workflow["on"]["push"]
        assert "branches" not in push_config, "Should not trigger on branch pushes"


class TestWorkflowBuildMatrix:
    def test_has_build_job(self, workflow):
        assert "build" in workflow["jobs"]

    def test_has_four_platform_combinations(self, workflow):
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        assert len(matrix) == 4, f"Expected 4 platform combos, got {len(matrix)}"

    def test_covers_darwin_arm64(self, workflow):
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        platforms = [(m["platform"], m["arch"]) for m in matrix]
        assert ("darwin", "arm64") in platforms

    def test_covers_darwin_amd64(self, workflow):
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        platforms = [(m["platform"], m["arch"]) for m in matrix]
        assert ("darwin", "amd64") in platforms

    def test_covers_linux_amd64(self, workflow):
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        platforms = [(m["platform"], m["arch"]) for m in matrix]
        assert ("linux", "amd64") in platforms

    def test_covers_linux_arm64(self, workflow):
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        platforms = [(m["platform"], m["arch"]) for m in matrix]
        assert ("linux", "arm64") in platforms

    def test_uses_python_313(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        python_step = next(s for s in steps if s.get("uses", "").startswith("actions/setup-python"))
        assert python_step["with"]["python-version"] == "3.13"

    def test_uses_uv(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        uv_steps = [s for s in steps if "astral-sh/setup-uv" in s.get("uses", "")]
        assert len(uv_steps) > 0, "Should set up uv"


class TestWorkflowBuildSteps:
    def test_build_step_uses_nuitka(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        build_step = next(s for s in steps if s.get("name") == "Build binary")
        assert "nuitka" in build_step["run"].lower()

    def test_build_step_produces_standalone(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        build_step = next(s for s in steps if s.get("name") == "Build binary")
        assert "--standalone" in build_step["run"] or "--onefile" in build_step["run"]

    def test_has_smoke_test(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        smoke_step = next(s for s in steps if s.get("name") == "Smoke test")
        assert "--help" in smoke_step["run"]

    def test_creates_tar_archive(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        archive_step = next(s for s in steps if s.get("name") == "Create archive")
        assert "tar" in archive_step["run"]
        assert ".tar.gz" in archive_step["run"]

    def test_generates_checksum(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        checksum_step = next(s for s in steps if s.get("name") == "Generate checksum")
        assert "sha256" in checksum_step["run"]

    def test_uploads_artifacts(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        upload_step = next(s for s in steps if s.get("name") == "Upload artifacts")
        assert "actions/upload-artifact" in upload_step["uses"]


class TestWorkflowReleaseJob:
    def test_has_release_job(self, workflow):
        assert "release" in workflow["jobs"]

    def test_release_depends_on_build(self, workflow):
        needs = workflow["jobs"]["release"]["needs"]
        assert "build" in (needs if isinstance(needs, list) else [needs])

    def test_release_has_write_permissions(self, workflow):
        perms = workflow["jobs"]["release"]["permissions"]
        assert perms.get("contents") == "write"

    def test_release_downloads_artifacts(self, workflow):
        steps = workflow["jobs"]["release"]["steps"]
        download_step = next(s for s in steps if "download-artifact" in s.get("uses", ""))
        assert download_step is not None

    def test_release_creates_github_release(self, workflow):
        steps = workflow["jobs"]["release"]["steps"]
        release_step = next(s for s in steps if "action-gh-release" in s.get("uses", ""))
        assert release_step is not None

    def test_release_attaches_binaries_and_checksums(self, workflow):
        steps = workflow["jobs"]["release"]["steps"]
        release_step = next(s for s in steps if "action-gh-release" in s.get("uses", ""))
        files = release_step["with"]["files"]
        assert "*.tar.gz" in files
        assert "*.sha256" in files
