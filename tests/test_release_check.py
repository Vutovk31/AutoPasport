from __future__ import annotations

import json
import subprocess

from scripts.release_check import CheckStep, build_steps, run_release_check, write_report


def completed(command, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(command, returncode, stdout=stdout, stderr=stderr)


def test_build_steps_covers_release_gates():
    names = [step.name for step in build_steps()]
    assert names == [
        "repository_privacy",
        "runtime_configuration",
        "database_migrations",
        "python_compilation",
        "test_suite",
        "restore_cli",
        "retention_cli",
        "docker_compose",
    ]


def test_skip_docker_removes_only_docker_step():
    names = [step.name for step in build_steps(skip_docker=True)]
    assert "docker_compose" not in names
    assert len(names) == 7


def test_release_report_collects_all_failures():
    steps = [CheckStep("first", ("first",)), CheckStep("second", ("second",))]

    def runner(command, **_kwargs):
        return completed(command, returncode=0 if command[0] == "first" else 3, stderr="boom")

    report = run_release_check(steps=steps, runner=runner)

    assert report["passed"] is False
    assert report["failed_steps"] == ["second"]
    assert report["summary"] == {"total": 2, "passed": 1, "failed": 1}
    assert report["steps"][1]["stderr"] == "boom"


def test_release_report_passes_when_every_step_passes():
    steps = [CheckStep("only", ("ok",))]
    report = run_release_check(steps=steps, runner=lambda command, **kwargs: completed(command, stdout="ok"))

    assert report["passed"] is True
    assert report["failed_steps"] == []
    assert report["steps"][0]["passed"] is True


def test_write_report_is_valid_json(tmp_path):
    path = tmp_path / "nested" / "release.json"
    payload = {"passed": True, "summary": {"total": 1}}

    write_report(path, payload)

    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert not path.with_suffix(".json.tmp").exists()
