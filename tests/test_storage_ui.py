from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_storage_usage_panel_is_present():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="storageCard"' in html
    assert 'id="storageAttachments"' in html
    assert 'id="storageBytes"' in html
    assert 'id="attachmentsProgress"' in html
    assert 'id="bytesProgress"' in html
    assert 'id="storageWarning"' in html


def test_storage_usage_api_and_thresholds_are_wired():
    javascript = (STATIC / "main.js").read_text(encoding="utf-8")
    assert "api('/api/me/storage')" in javascript
    assert "used < 80" in javascript
    assert "used >= 95" in javascript
    assert "owner_attachment_quota_exceeded" in javascript
    assert "owner_storage_quota_exceeded" in javascript
    assert "await refreshStorage()" in javascript


def test_pwa_assets_live_in_application_static_directory():
    required = [
        "index.html",
        "main.js",
        "styles.css",
        "manifest.webmanifest",
        "offline.html",
        "service-worker.js",
        "icons/icon-192.png",
        "icons/icon-512.png",
    ]
    for relative_path in required:
        assert (STATIC / relative_path).is_file(), relative_path
