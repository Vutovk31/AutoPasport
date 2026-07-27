#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable, Sequence

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: tuple[str, ...]


@dataclass
class StepResult:
    name: str
    command: list[str]
    returncode: int
    duration_ms: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


def build_steps(*, skip_docker: bool = False) -> list[CheckStep]:
    python = sys.executable
    steps = [
        CheckStep("repository_privacy", (python, "scripts/check_repository_privacy.py")),
        CheckStep("runtime_configuration", (python, "scripts/check_config.py")),
        CheckStep("database_migrations", ("alembic", "upgrade", "head")),
        CheckStep("python_compilation", (python, "-m", "compileall", "-q", "app", "scripts")),
        CheckStep("test_suite", (python, "-m", "pytest", "-q")),
        CheckStep("restore_cli", (python, "scripts/restore_backup.py", "--help")),
        CheckStep("retention_cli", (python, "scripts/cleanup_attachments.py", "--help")),
    ]
    if not skip_docker:
        steps.append(CheckStep("docker_compose", ("docker", "compose", "config", "-q")))
    return steps


def _tail(value: str, limit: int = 12000) -> str:
    return value if len(value) <= limit else value[-limit:]


def execute_step(
    step: CheckStep,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> StepResult:
    started = time.monotonic()
    completed = runner(
        list(step.command),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    duration_ms = round((time.monotonic() - started) * 1000)
    return StepResult(
        name=step.name,
        command=list(step.command),
        returncode=int(completed.returncode),
        duration_ms=duration_ms,
        stdout=_tail(completed.stdout or ""),
        stderr=_tail(completed.stderr or ""),
    )


def run_release_check(
    *,
    steps: Sequence[CheckStep] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict:
    selected = list(steps or build_steps())
    started_at = datetime.now(timezone.utc)
    results = [execute_step(step, runner=runner) for step in selected]
    finished_at = datetime.now(timezone.utc)
    failed = [result.name for result in results if not result.passed]
    return {
        "schema_version": 1,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "passed": not failed,
        "failed_steps": failed,
        "summary": {
            "total": len(results),
            "passed": sum(result.passed for result in results),
            "failed": len(failed),
        },
        "steps": [asdict(result) | {"passed": result.passed} for result in results],
    }


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def default_report_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return ROOT / "data" / "reports" / f"release-check-{stamp}.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the complete AutoPassport release verification suite.")
    parser.add_argument("--report-path", type=Path, help="JSON report destination.")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker Compose validation.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report_path = (args.report_path or default_report_path()).expanduser().resolve()
    report = run_release_check(steps=build_steps(skip_docker=args.skip_docker))
    report["report_path"] = str(report_path)
    write_report(report_path, report)
    print(json.dumps({
        "passed": report["passed"],
        "summary": report["summary"],
        "failed_steps": report["failed_steps"],
        "report_path": str(report_path),
    }, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
