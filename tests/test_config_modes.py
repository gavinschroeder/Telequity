"""Config scope modes: national vs single-state."""
from telequity.config import Config


def _cfg(scope):
    return Config(raw={"scope": scope, "paths": {}}, root=None)


def test_national_mode():
    c = _cfg({"mode": "national", "state_fips": None, "state_abbr": None})
    assert c.is_national is True
    assert c.scope_slug == "us"


def test_state_mode():
    c = _cfg({"mode": "state", "state_fips": "48", "state_abbr": "TX"})
    assert c.is_national is False
    assert c.scope_slug == "tx"


def test_blank_state_defaults_to_national():
    c = _cfg({"state_fips": None})
    assert c.is_national is True
