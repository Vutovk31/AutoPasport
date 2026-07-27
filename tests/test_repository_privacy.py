from pathlib import Path
import importlib.util


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "check_repository_privacy.py"
    spec = importlib.util.spec_from_file_location("check_repository_privacy", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def make_required(root: Path, module):
    for relative in module.REQUIRED_PATHS:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("safe content\n", encoding="utf-8")


def test_clean_repository_passes(tmp_path):
    module = load_module()
    make_required(tmp_path, module)
    assert module.scan_repository(tmp_path) == []


def test_missing_required_file_is_reported(tmp_path):
    module = load_module()
    make_required(tmp_path, module)
    (tmp_path / "app/main.py").unlink()
    assert "missing required file: app/main.py" in module.scan_repository(tmp_path)


def test_private_env_and_database_are_rejected(tmp_path):
    module = load_module()
    make_required(tmp_path, module)
    (tmp_path / ".env").write_text("SECRET=value", encoding="utf-8")
    data = tmp_path / "data"
    data.mkdir()
    (data / "autopassport.db").write_bytes(b"sqlite")
    errors = module.scan_repository(tmp_path)
    assert "forbidden private file: .env" in errors
    assert "forbidden private file: data/autopassport.db" in errors


def test_secret_and_private_key_patterns_are_rejected(tmp_path):
    module = load_module()
    make_required(tmp_path, module)
    github_token = "ghp_" + ("A" * 30)
    private_key_header = "-----BEGIN " + "PRIVATE KEY-----"
    (tmp_path / "leak.txt").write_text(
        github_token + "\n" + private_key_header + "\n",
        encoding="utf-8",
    )
    errors = module.scan_repository(tmp_path)
    assert "possible GitHub token in leak.txt" in errors
    assert "possible private key in leak.txt" in errors


def test_real_vin_pattern_is_rejected_outside_allowlist(tmp_path):
    module = load_module()
    make_required(tmp_path, module)
    vin_like_value = "WVWZZZ1JZX" + "W000001"
    (tmp_path / "notes.md").write_text(vin_like_value, encoding="utf-8")
    assert "possible real VIN in public file: notes.md" in module.scan_repository(tmp_path)
