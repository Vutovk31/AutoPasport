from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"


def test_share_usage_card_is_present():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    for marker in (
        'id="shareUsageCard"',
        'id="shareSummary"',
        'id="shareLinks"',
        'id="shareProgress"',
        'id="shareWarning"',
        'id="refreshShares"',
    ):
        assert marker in html


def test_share_usage_frontend_contract():
    js = (STATIC / "main.js").read_text(encoding="utf-8")
    assert "api('/api/me/shares')" in js
    assert "renderShares" in js
    assert "refreshShares" in js
    assert "active_links" in js
    assert "max_active_links" in js
    assert "remaining_links" in js
    assert "percent < 80" in js
    assert "percent >= 100" in js


def test_share_quota_errors_are_user_readable():
    js = (STATIC / "main.js").read_text(encoding="utf-8")
    assert "vehicle_share_link_quota_exceeded" in js
    assert "owner_share_link_quota_exceeded" in js
    assert "Для этого автомобиля" in js
    assert "общий лимит активных публичных ссылок" in js


def test_share_usage_refreshes_after_create_attempt():
    js = (STATIC / "main.js").read_text(encoding="utf-8")
    handler = js.split("$('#share').onclick", 1)[1]
    assert handler.count("await refreshShares()") >= 2
    assert "alert(error.message)" in handler
