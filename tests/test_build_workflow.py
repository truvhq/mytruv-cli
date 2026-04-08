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
        python_step = next((s for s in steps if s.get("uses", "").startswith("actions/setup-python")), None)
        assert python_step is not None, "Expected step 'actions/setup-python' not found"
        assert python_step["with"]["python-version"] == "3.13"

    def test_uses_uv(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        uv_steps = [s for s in steps if "astral-sh/setup-uv" in s.get("uses", "")]
        assert len(uv_steps) > 0, "Should set up uv"

    def test_darwin_amd64_uses_intel_runner(self, workflow):
        """darwin/amd64 must run on an Intel (x86_64) macOS runner, not ARM."""
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        entry = next(m for m in matrix if m["platform"] == "darwin" and m["arch"] == "amd64")
        assert "macos-13" in entry["os"], (
            f"darwin/amd64 must use macos-13 (Intel), not {entry['os']} (ARM)"
        )

    def test_linux_arm64_uses_arm_runner(self, workflow):
        """linux/arm64 must run on an ARM runner, not x86_64."""
        matrix = workflow["jobs"]["build"]["strategy"]["matrix"]["include"]
        entry = next(m for m in matrix if m["platform"] == "linux" and m["arch"] == "arm64")
        assert "arm" in entry["os"].lower() or "aarch64" in entry["os"].lower(), (
            f"linux/arm64 must use an ARM runner, not {entry['os']} (x86_64)"
        )

    def test_actions_pinned_to_commit_shas(self, workflow):
        """Third-party actions should be pinned to commit SHAs, not mutable tags."""
        steps = workflow["jobs"]["build"]["steps"]
        release_steps = workflow["jobs"]["release"]["steps"]
        all_steps = steps + release_steps
        for step in all_steps:
            uses = step.get("uses", "")
            if not uses:
                continue
            # Check the ref after @ is a commit SHA (40 hex chars), not a tag like v4
            import re

            ref = uses.split("@")[-1] if "@" in uses else ""
            assert re.fullmatch(r"[0-9a-f]{40}", ref), (
                f"Action '{uses}' should be pinned to a full 40-char hex commit SHA, not '{ref}'"
            )


class TestWorkflowBuildSteps:
    def test_build_step_uses_nuitka(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        build_step = next((s for s in steps if s.get("name") == "Build binary"), None)
        assert build_step is not None, "Expected step 'Build binary' not found"
        assert "nuitka" in build_step["run"].lower()

    def test_build_step_produces_standalone(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        build_step = next((s for s in steps if s.get("name") == "Build binary"), None)
        assert build_step is not None, "Expected step 'Build binary' not found"
        assert "--standalone" in build_step["run"] or "--onefile" in build_step["run"]

    def test_has_smoke_test(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        smoke_step = next((s for s in steps if s.get("name") == "Smoke test"), None)
        assert smoke_step is not None, "Expected step 'Smoke test' not found"
        assert "--help" in smoke_step["run"]

    def test_creates_tar_archive(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        archive_step = next((s for s in steps if s.get("name") == "Create archive"), None)
        assert archive_step is not None, "Expected step 'Create archive' not found"
        assert "tar" in archive_step["run"]
        assert ".tar.gz" in archive_step["run"]

    def test_generates_checksum(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        checksum_step = next((s for s in steps if s.get("name") == "Generate checksum"), None)
        assert checksum_step is not None, "Expected step 'Generate checksum' not found"
        assert "sha256" in checksum_step["run"]

    def test_uploads_artifacts(self, workflow):
        steps = workflow["jobs"]["build"]["steps"]
        upload_step = next((s for s in steps if s.get("name") == "Upload artifacts"), None)
        assert upload_step is not None, "Expected step 'Upload artifacts' not found"
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
        download_step = next((s for s in steps if "download-artifact" in s.get("uses", "")), None)
        assert download_step is not None, "Expected download-artifact step not found"

    def test_release_creates_github_release(self, workflow):
        steps = workflow["jobs"]["release"]["steps"]
        release_step = next((s for s in steps if "action-gh-release" in s.get("uses", "")), None)
        assert release_step is not None, "Expected action-gh-release step not found"

    def test_release_attaches_binaries_and_checksums(self, workflow):
        steps = workflow["jobs"]["release"]["steps"]
        release_step = next((s for s in steps if "action-gh-release" in s.get("uses", "")), None)
        assert release_step is not None, "Expected action-gh-release step not found"
        files = release_step["with"]["files"]
        assert "*.tar.gz" in files
        assert "*.sha256" in files
