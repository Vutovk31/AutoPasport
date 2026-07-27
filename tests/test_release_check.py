from __future__ import annotations

import json
import subprocess

from scripts.release_check import (
    COMMAND_NOT_FOUND_RETURN_CODE,
    COMMAND_TIMEOUT_RETURN_CODE,
    CheckStep,
    build_steps,
    run_release_check,
    write_report,
)


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
    assert all(step.timeout_seconds > 0 for step in build_steps())


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


def test_missing_command_is_recorded_and_later_steps_continue():
    steps = [CheckStep("missing", ("missing",)), CheckStep("later", ("later",))]

    def runner(command, **_kwargs):
        if command[0] == "missing":
            raise FileNotFoundError("missing executable")
        return completed(command, stdout="continued")

    report = run_release_check(steps=steps, runner=runner)

    assert report["failed_steps"] == ["missing"]
    assert report["steps"][0]["returncode"] == COMMAND_NOT_FOUND_RETURN_CODE
    assert "Command unavailable" in report["steps"][0]["stderr"]
    assert report["steps"][1]["passed"] is True


def test_timed_out_command_is_recorded_with_partial_output():
    step = CheckStep("slow", ("slow",), timeout_seconds=7)

    def runner(command, **_kwargs):
        raise subprocess.TimeoutExpired(command, 7, output="partial output", stderr="partial error")

    report = run_release_check(steps=[step], runner=runner)

    result = report["steps"][0]
    assert result["returncode"] == COMMAND_TIMEOUT_RETURN_CODE
    assert result["stdout"] == "partial output"
    assert "partial error" in result["stderr"]
    assert "timed out after 7 seconds" in result["stderr"]


def test_runner_receives_step_timeout():
    captured = {}

    def runner(command, **kwargs):
        captured.update(kwargs)
        return completed(command)

    run_release_check(steps=[CheckStep("only", ("ok",), timeout_seconds=33)], runner=runner)

    assert captured["timeout"] == 33


def test_write_report_is_valid_json(tmp_path):
    path = tmp_path / "nested" / "release.json"
    payload = {"passed": True, "summary": {"total": 1}}

    write_report(path, payload)

    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert not path.with_suffix(".json.tmp").exists()