"""Define tests for the Music Assistant Integration config flow."""

from unittest import mock
from unittest.mock import patch

from homeassistant.helpers.selector import ConversationAgentSelector
from music_assistant.client.exceptions import CannotConnect, InvalidServerVersion

from custom_components.mass import config_flow
from custom_components.mass.config_flow import (
    CONF_ASSIST_AUTO_EXPOSE_PLAYERS,
    CONF_INTEGRATION_CREATED_ADDON,
    CONF_OPENAI_AGENT_ID,
    CONF_URL,
    CONF_USE_ADDON,
)

DEFAULT_TITLE = "Music Assistant"

VALID_CONFIG = {
    CONF_URL: "http://localhost:8095",
    CONF_USE_ADDON: True,
    CONF_INTEGRATION_CREATED_ADDON: True,
    CONF_OPENAI_AGENT_ID: "2be183ad64ff0d464a94bd2915140a55",
    CONF_ASSIST_AUTO_EXPOSE_PLAYERS: True,
}


async def test_flow_user_init_manual_schema(hass):
    """Test the initialization of the form in the first step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    user_input = {CONF_URL: "http://localhost:8095"}
    expected = {
        "data_schema": config_flow.get_manual_schema(user_input=user_input),
        "description_placeholders": None,
        "errors": None,
        "flow_id": mock.ANY,
        "handler": "mass",
        "step_id": "manual",
        "last_step": None,
        "preview": None,
        "type": "form",
    }

    assert result.get("step_id") == expected.get("step_id")
    data_schema = result.get("data_schema")
    assert data_schema is not None
    assert data_schema.schema[CONF_URL] is str
    assert isinstance(data_schema.schema[CONF_OPENAI_AGENT_ID], ConversationAgentSelector)
    assert data_schema.schema[CONF_ASSIST_AUTO_EXPOSE_PLAYERS] is bool


async def test_flow_user_init_supervisor_schema(hass):
    """Test the initialization of the form in the first step of the config flow."""
    hass.config.components.add("hassio")
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    expected = {
        "data_schema": config_flow.ON_SUPERVISOR_SCHEMA,
        "description_placeholders": None,
        "errors": None,
        "flow_id": mock.ANY,
        "handler": "mass",
        "step_id": "on_supervisor",
        "last_step": None,
        "preview": None,
        "type": "form",
    }
    assert result.get("step_id") == expected.get("step_id")
    data_schema = result.get("data_schema")
    assert data_schema is not None
    assert data_schema.schema[CONF_USE_ADDON] is bool
    assert isinstance(data_schema.schema[CONF_OPENAI_AGENT_ID], ConversationAgentSelector)
    assert data_schema.schema[CONF_ASSIST_AUTO_EXPOSE_PLAYERS] is bool


@patch("custom_components.mass.config_flow.get_server_info")
async def test_flow_user_init_connect_issue(m_server_info, hass):
    """Test we advance to the next step when server url is invalid."""
    m_server_info.side_effect = CannotConnect("cannot_connect")

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_URL: "bad"}
    )
    assert {"base": "cannot_connect"} == result["errors"]


@patch("custom_components.mass.config_flow.get_server_info")
async def test_flow_user_init_server_version_invalid(m_server_info, hass):
    """Test we advance to the next step when server url is invalid."""
    m_server_info.side_effect = InvalidServerVersion("invalid_server_version")

    _result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        _result["flow_id"], user_input={CONF_URL: "bad"}
    )
    assert {"base": "invalid_server_version"} == result["errors"]
