from __future__ import annotations

from tradeo.modules.fox_hunter.scanner import FoxHunterScanner
from tradeo.modules.laboratory.scanner import LaboratoryScanner


def test_laboratory_scanner_uses_laboratory_module(monkeypatch) -> None:
    calls: list[str] = []

    def fake_scan(self, db, *, module, **kwargs):
        calls.append(module)
        return {"module": module, **kwargs}

    monkeypatch.setattr("tradeo.modules.laboratory.scanner.PatternEntryScanner.scan", fake_scan)

    result = LaboratoryScanner().scan(
        object(),
        symbols=["AAPL"],
        limit=3,
        max_patterns=2,
        similarity_threshold=0.5,
        store_signals=True,
        execute_orders=False,
    )

    assert calls == ["laboratory"]
    assert result["module"] == "laboratory"
    assert result["symbols"] == ["AAPL"]


def test_fox_hunter_scanner_uses_fox_hunter_module(monkeypatch) -> None:
    calls: list[str] = []

    def fake_scan(self, db, *, module, **kwargs):
        calls.append(module)
        return {"module": module, **kwargs}

    monkeypatch.setattr("tradeo.modules.fox_hunter.scanner.PatternEntryScanner.scan", fake_scan)

    result = FoxHunterScanner().scan(
        object(),
        symbols=["MSFT"],
        limit=5,
        max_patterns=1,
        similarity_threshold=0.7,
        store_signals=True,
        execute_orders=True,
    )

    assert calls == ["fox_hunter"]
    assert result["module"] == "fox_hunter"
    assert result["symbols"] == ["MSFT"]

