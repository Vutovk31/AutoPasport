from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

REQUIRED_PATHS = {
    "app/main.py",
    "app/models.py",
    "app/database.py",
    "app/config.py",
    "alembic/env.py",
    "scripts/entrypoint.sh",
    "scripts/check_config.py",
    "tests/test_mvp.py",
    ".github/workflows/ci.yml",
    "VERSION",
}

FORBIDDEN_NAMES = {".env", "private_vehicle.json", "autopassport.db"}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "OpenAI key": re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}
VIN_PATTERN = re.compile(r"\b[A-HJ-NPR-Z0-9]{17}\b")
TEXT_SUFFIXES = {".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".ini", ".html", ".js", ".css", ".sh", ""}
VIN_ALLOWLIST_PATHS = {"sample_data/local_seed.example.json", "sample_data/private_vehicle.template.json", "tests/test_mvp.py"}


def scan_repository(root: Path) -> list[str]:
    errors: list[str] = []
    for required in sorted(REQUIRED_PATHS):
        if not (root / required).is_file():
            errors.append(f"missing required file: {required}")

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        relative = path.relative_to(root).as_posix()
        if path.name in FORBIDDEN_NAMES:
            errors.append(f"forbidden private file: {relative}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden credential file: {relative}")
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                errors.append(f"possible {label} in {relative}")
        if relative not in VIN_ALLOWLIST_PATHS and VIN_PATTERN.search(text):
            errors.append(f"possible real VIN in public file: {relative}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public repository structure and privacy")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()
    errors = scan_repository(Path(args.root).resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository privacy gate: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
