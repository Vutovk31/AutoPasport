import json

from app import document_parser_worker
from app.document_parser_recovery import ParserRecoveryReport


class FakeSession:
    def __init__(self):
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_worker_runs_one_bounded_sweep_and_closes_session(monkeypatch):
    session = FakeSession()
    calls = []

    def recover(fake_session, *, limit, minimum_age_seconds):
        calls.append((fake_session, limit, minimum_age_seconds))
        return ParserRecoveryReport(scanned=3, accepted=2, declined=1)

    monkeypatch.setattr(document_parser_worker, "recover_unqueued_documents", recover)

    report = document_parser_worker.run_recovery_worker(
        session_factory=lambda: session,
        limit=25,
        minimum_age_seconds=90,
    )

    assert report == ParserRecoveryReport(scanned=3, accepted=2, declined=1)
    assert calls == [(session, 25, 90)]
    assert session.closed is True


def test_worker_closes_session_when_sweep_fails(monkeypatch):
    session = FakeSession()

    def recover(*args, **kwargs):
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(document_parser_worker, "recover_unqueued_documents", recover)

    try:
        document_parser_worker.run_recovery_worker(session_factory=lambda: session)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError")

    assert session.closed is True


def test_main_emits_safe_operational_report(monkeypatch, capsys):
    monkeypatch.setattr(
        document_parser_worker,
        "run_recovery_worker",
        lambda **kwargs: ParserRecoveryReport(scanned=4, accepted=3, declined=1),
    )

    exit_code = document_parser_worker.main(
        ["--limit", "40", "--minimum-age-seconds", "60"],
        session_factory=FakeSession,
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "ok",
        "scanned": 4,
        "accepted": 3,
        "declined": 1,
    }


def test_main_returns_nonzero_without_writing_failure_to_stdout(monkeypatch, capsys):
    def fail(**kwargs):
        raise RuntimeError("temporary failure")

    monkeypatch.setattr(document_parser_worker, "run_recovery_worker", fail)

    exit_code = document_parser_worker.main([], session_factory=FakeSession)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""


def test_cli_accepts_recovery_boundary_limits():
    parser = document_parser_worker.build_parser()
    args = parser.parse_args(["--limit", "1000", "--minimum-age-seconds", "0"])

    assert args.limit == 1000
    assert args.minimum_age_seconds == 0
