from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "app" / "static" / "index.html"
MAIN = ROOT / "app" / "static" / "main.js"
STYLES = ROOT / "app" / "static" / "styles.css"


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()

    def handle_starttag(self, _tag, attrs):
        for name, value in attrs:
            if name == "id":
                self.ids.add(value)


def test_scan_screen_has_explicit_vehicle_context_and_escape_route():
    parser = IdCollector()
    parser.feed(INDEX.read_text(encoding="utf-8"))

    assert {
        "scanVehicleContext",
        "scanVehicleSelected",
        "scanVehicleEmpty",
        "scanVehicleName",
        "scanVehicleMeta",
        "changeScanVehicle",
        "scanAddVehicle",
    } <= parser.ids


def test_selected_vehicle_identity_is_rendered_without_html_injection():
    source = MAIN.read_text(encoding="utf-8")

    assert "function renderScanVehicleContext(vehicle = null)" in source
    assert "$('#scanVehicleName').textContent" in source
    assert "$('#scanVehicleMeta').textContent" in source
    assert "maskVin(vehicle.vin)" in source
    assert "uploadButton.disabled = !vehicle" in source
    assert "renderScanVehicleContext(rows.find" in source


def test_change_vehicle_returns_to_garage_and_restores_focus():
    source = MAIN.read_text(encoding="utf-8")

    assert "changeScanVehicle.onclick" in source
    assert "setView('home')" in source
    assert "vehicle-card.active[data-id]" in source
    assert "requestAnimationFrame" in source


def test_vehicle_context_controls_meet_mobile_accessibility_baseline():
    source = STYLES.read_text(encoding="utf-8")

    assert ".scan-vehicle-change" in source
    assert "min-height:44px" in source
    assert "button:focus-visible" in source
    assert "@media(prefers-reduced-motion:reduce)" in source
