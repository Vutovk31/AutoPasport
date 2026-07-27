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


def test_ci_publishes_explicit_commit_status_for_connector_visibility():
    text = workflow_text()
    status = text.index('Publish explicit release commit status')
    artifact = text.index('Publish release verification report')
    assert status < artifact
    assert 'statuses: write' in text
    assert 'if: always()' in text[status:artifact]
    assert 'actions/github-script@v7' in text[status:artifact]
    assert "context: 'autopassport/release-check'" in text[status:artifact]
    assert "state: passed ? 'success' : 'failure'" in text[status:artifact]
    assert 'createCommitStatus' in text[status:artifact]


def test_commit_status_uses_bootstrap_report_as_failure_fallback():
    text = workflow_text()
    status = text.index('Publish explicit release commit status')
    artifact = text.index('Publish release verification report')
    block = text[status:artifact]
    assert "failed_steps: ['report_unavailable']" in block
    assert "report.passed === true && failed.length === 0" in block
    assert 'description.slice(0, 140)' in block
    assert 'context.runId' in block
