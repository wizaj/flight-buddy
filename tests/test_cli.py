"""Tests for Flight Buddy CLI."""

import pytest
from click.testing import CliRunner

from app.cli import cli, parse_cabin, parse_date, parse_flight_number


class TestHelpers:
    """Test helper functions."""
    
    def test_parse_cabin_shortcuts(self):
        assert parse_cabin("j") == "BUSINESS"
        assert parse_cabin("J") == "BUSINESS"
        assert parse_cabin("business") == "BUSINESS"
        assert parse_cabin("biz") == "BUSINESS"
        
        assert parse_cabin("y") == "ECONOMY"
        assert parse_cabin("economy") == "ECONOMY"
        assert parse_cabin("eco") == "ECONOMY"
        
        assert parse_cabin("f") == "FIRST"
        assert parse_cabin("first") == "FIRST"
        
        assert parse_cabin("w") == "PREMIUM_ECONOMY"
        assert parse_cabin("premium") == "PREMIUM_ECONOMY"
        
        assert parse_cabin(None) is None
    
    def test_parse_date_shortcuts(self):
        from datetime import date, timedelta
        
        today = date.today().isoformat()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        
        assert parse_date("today") == today
        assert parse_date("TODAY") == today
        assert parse_date("tomorrow") == tomorrow
        assert parse_date("2026-02-15") == "2026-02-15"
    
    def test_parse_flight_number_valid(self):
        assert parse_flight_number("EK766") == ("EK", "766")
        assert parse_flight_number("ek766") == ("EK", "766")
        assert parse_flight_number("QR1369") == ("QR", "1369")
        assert parse_flight_number("AA1") == ("AA", "1")
    
    def test_parse_flight_number_invalid(self):
        import click
        
        with pytest.raises(click.BadParameter):
            parse_flight_number("invalid")
        
        with pytest.raises(click.BadParameter):
            parse_flight_number("EK")
        
        with pytest.raises(click.BadParameter):
            parse_flight_number("766")


class TestCLI:
    """Test CLI commands."""
    
    @pytest.fixture
    def runner(self):
        return CliRunner()
    
    def test_help(self, runner):
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Flight Buddy" in result.output
        assert "search" in result.output
        assert "flight" in result.output
        assert "avail" in result.output
        assert "seats" in result.output
    
    def test_search_help(self, runner):
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search for flights" in result.output
        assert "--cabin" in result.output
        assert "--direct" in result.output
    
    def test_flight_help(self, runner):
        result = runner.invoke(cli, ["flight", "--help"])
        assert result.exit_code == 0
        assert "Look up a flight" in result.output
    
    def test_avail_help(self, runner):
        result = runner.invoke(cli, ["avail", "--help"])
        assert result.exit_code == 0
        assert "seat availability" in result.output
    
    def test_seats_help(self, runner):
        result = runner.invoke(cli, ["seats", "--help"])
        assert result.exit_code == 0
        assert "seat map" in result.output
