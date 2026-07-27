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
DEFAULT_STEP_TIMEOUT_SECONDS = 1200
COMMAND_NOT_FOUND_RETURN_CODE = 127
COMMAND_TIMEOUT_RETURN_CODE = 124


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: tuple[str, ...]
    timeout_seconds: int = DEFAULT_STEP_TIMEOUT_SECONDS


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
        CheckStep("repository_privacy", (python, "scripts/check_repository_privacy.py"), 120),
        CheckStep("runtime_configuration", (python, "scripts/check_config.py"), 120),
        CheckStep("database_migrations", ("alembic", "upgrade", "head"), 300),
        CheckStep("python_compilation", (python, "-m", "compileall", "-q", "app", "scripts"), 180),
        CheckStep("test_suite", (python, "-m", "pytest", "-q"), 1200),
        CheckStep("restore_cli", (python, "scripts/restore_backup.py", "--help"), 120),
        CheckStep("retention_cli", (python, "scripts/cleanup_attachments.py", "--help"), 120),
    ]
    if not skip_docker:
        steps.append(CheckStep("docker_compose", ("docker", "compose", "--env-file", ".env.example", "config", "-q"), 180))
    return steps


def _tail(value: str, limit: int = 12000) -> str:
    return value if len(value) <= limit else value[-limit:]


def _stream_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def execute_step(
    step: CheckStep,
    *,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> StepResult:
    started = time.monotonic()
    try:
        completed = runner(
            list(step.command),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=step.timeout_seconds,
        )
        returncode = int(completed.returncode)
        stdout = _stream_text(completed.stdout)
        stderr = _stream_text(completed.stderr)
    except FileNotFoundError as exc:
        returncode = COMMAND_NOT_FOUND_RETURN_CODE
        stdout = ""
        stderr = f"Command unavailable: {exc}"
    except subprocess.TimeoutExpired as exc:
        returncode = COMMAND_TIMEOUT_RETURN_CODE
        stdout = _stream_text(exc.stdout)
        stderr = _stream_text(exc.stderr)
        suffix = f"Command timed out after {step.timeout_seconds} seconds"
        stderr = f"{stderr.rstrip()}\n{suffix}" if stderr else suffix
    except OSError as exc:
        returncode = COMMAND_NOT_FOUND_RETURN_CODE
        stdout = ""
        stderr = f"Command execution failed: {exc}"

    duration_ms = round((time.monotonic() - started) * 1000)
    return StepResult(
        name=step.name,
        command=list(step.command),
        returncode=returncode,
        duration_ms=duration_ms,
        stdout=_tail(stdout),
        stderr=_tail(stderr),
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
