from pathlib import Path


WORKFLOW = Path('.github/workflows/ci.yml')


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding='utf-8')


def test_ci_supports_manual_release_verification():
    text = workflow_text()
    assert 'workflow_dispatch:' in text


def test_ci_bootstraps_report_before_dependency_installation():
    text = workflow_text()
    bootstrap = text.index('Bootstrap release verification report')
    install = text.index('Install dependencies')
    release = text.index('Run complete release verification')
    assert bootstrap < install < release
    assert '"status": "bootstrap"' in text
    assert '"passed": false' in text


def test_ci_always_publishes_report_artifact():
    text = workflow_text()
    publish = text.index('Publish release verification report')
    assert 'if: always()' in text[publish:]
    assert 'if-no-files-found: error' in text[publish:]
    assert 'data/reports/release-check.json' in text[publish:]
