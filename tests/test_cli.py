"""Tests for Oopple Typer CLI commands."""

from typer.testing import CliRunner

from oopple.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Intelligent Nutrition" in result.output


def test_cli_water_flow():
    # Test logging water
    log_result = runner.invoke(app, ["water", "log", "500", "--source", "Filtered Tap"])
    assert log_result.exit_code == 0
    assert "Logged +500.0ml" in log_result.output
    assert "Trust us, your body likes water" in log_result.output

    # Test checking status
    status_result = runner.invoke(app, ["water", "status"])
    assert status_result.exit_code == 0
    assert "Hydration Balance Radar" in status_result.output


def test_cli_ledger_verify():
    result = runner.invoke(app, ["ledger", "verify"])
    assert result.exit_code == 0
    assert "Ledger Cryptographic Integrity Valid" in result.output
