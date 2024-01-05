"""Define tests for the Music Assistant Integration config flow."""
from unittest.mock import patch

from homeassistant import config_entries, setup

from custom_components.mass.config_flow import (
    CONF_ASSIST_AUTO_EXPOSE_PLAYERS,
    CONF_INTEGRATION_CREATED_ADDON,
    CONF_OPENAI_AGENT_ID,
    CONF_URL,
    CONF_USE_ADDON,
)
from custom_components.mass.const import DOMAIN

DEFAULT_TITLE = "Music Assistant"

VALID_CONFIG = {
    CONF_URL: "http://localhost:8095",
    CONF_USE_ADDON: True,
    CONF_INTEGRATION_CREATED_ADDON: True,
    CONF_OPENAI_AGENT_ID: "32-character-string-1234567890qw",
    CONF_ASSIST_AUTO_EXPOSE_PLAYERS: True,
}


async def test_form(hass):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == "form"
    assert result["errors"] == {}

    with patch(
        "custom_components.mass.config_flow.async_sep_user", return_value=True





async def test_show_form(hass) -> None:
    """Test that the form is served with no input."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})

    assert result["type"] == "form"
    assert result["step_id"] == "manual"


async def test_create_entry(hass) -> None:
    """Test that the user step works."""
    with patch("custom_components.mass.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": config_entries.SOURCE_USER},
            data=VALID_CONFIG,
        )

        assert result2["type"] == "form"
        assert result2["title"] == DEFAULT_TITLE
        assert result2["data"][CONF_URL] == "http://localhost:8095"
        assert result2["data"][CONF_USE_ADDON] is True
        assert result2["data"][CONF_INTEGRATION_CREATED_ADDON] is True
        assert result2["data"][CONF_OPENAI_AGENT_ID] == "32-character-string-1234567890qw"
        assert result2["data"][CONF_ASSIST_AUTO_EXPOSE_PLAYERS] is True
