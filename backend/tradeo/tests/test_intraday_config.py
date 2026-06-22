from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tradeo.core.config import Settings


def test_intraday_defaults_are_off_and_live_blocked() -> None:
    settings = Settings()

    assert settings.intraday_enabled is False
    assert settings.intraday_shadow_enabled is False
    assert settings.intraday_paper_enabled is False
    assert settings.intraday_live_enabled is False
    assert settings.intraday_live_armed is False
    assert "intraday_disabled" in settings.intraday_live_config_blockers
    assert settings.intraday_timeframe_list == ["15m", "5m"]


def test_intraday_live_fails_closed_without_required_gates() -> None:
    with pytest.raises(ValidationError, match="intraday live is blocked"):
        Settings(intraday_live_enabled=True)


def test_config_doctor_lists_keys_only_and_redacts_secrets(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    example_file = tmp_path / ".env.example"
    env_file.write_text(
        "\n".join(
            [
                "TRADEO_SECRET_" + "KEY=real-secret-value",
                "TRADEO_ADMIN_" + "PASSWORD=real-password",
                "TRADEO_UNDOCUMENTED_FLAG=true",
            ]
        ),
        encoding="utf-8",
    )
    example_file.write_text(
        "\n".join(
            [
                "TRADEO_SECRET_KEY=replace-me",
                "TRADEO_ADMIN_PASSWORD=replace-me",
                "TRADEO_INTRADAY_ENABLED=false",
            ]
        ),
        encoding="utf-8",
    )

    report = Settings().config_doctor(env_path=env_file, example_path=example_file)
    rendered = repr(report)

    assert report["redacted"] is True
    assert report["secret_values_exposed"] is False
    assert "real-secret-value" not in rendered
    assert "real-password" not in rendered
    assert "TRADEO_UNDOCUMENTED_FLAG" in report["env"]["undocumented_tradeo_keys"]
    assert "TRADEO_INTRADAY_ENABLED" in report["env"]["missing_keys"]


def test_config_doctor_env_example_documents_all_intraday_keys() -> None:
    report = Settings().config_doctor(
        env_path=Path("missing.env"),
        example_path=Path("../.env.example"),
    )

    assert report["intraday"]["missing_example_keys"] == []
