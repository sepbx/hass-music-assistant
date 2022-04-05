"""Music Assistant (music-assistant.github.io) integration."""

from typing import Any

from custom_components.music_assistant.player_controls import HassPlayerControls
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_CALL_SERVICE, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import HomeAssistantType
from music_assistant import MusicAssistant
from music_assistant.constants import EventType
from music_assistant.models.errors import MusicAssistantError
from music_assistant.providers.qobuz import QobuzProvider
from music_assistant.providers.spotify import SpotifyProvider
from music_assistant.providers.tunein import TuneInProvider

from .const import (
    CONF_CREATE_MASS_PLAYERS,
    CONF_QOBUZ_ENABLED,
    CONF_QOBUZ_PASSWORD,
    CONF_QOBUZ_USERNAME,
    CONF_SPOTIFY_ENABLED,
    CONF_SPOTIFY_PASSWORD,
    CONF_SPOTIFY_USERNAME,
    CONF_TUNEIN_ENABLED,
    CONF_TUNEIN_USERNAME,
    DISPATCH_KEY_QUEUE_ADDED,
    DISPATCH_KEY_QUEUE_UPDATE,
    DOMAIN,
)


async def async_setup(hass, config):
    """Set up the platform."""
    hass.data[DOMAIN] = None
    return True


async def async_setup_entry(hass: HomeAssistantType, entry: ConfigEntry):
    """Set up from a config entry."""
    http_session = async_get_clientsession(hass, verify_ssl=False)
    # TODO: optionally use mysql if mysql is detected ?
    db_file = hass.config.path("music_assistant.db")
    mass = MusicAssistant(f"sqlite:///{db_file}", session=http_session)
    conf = entry.options
    try:
        await mass.setup()
        # register music providers
        if conf.get(CONF_SPOTIFY_ENABLED):
            await mass.music.register_provider(
                SpotifyProvider(
                    conf.get(CONF_SPOTIFY_USERNAME), conf.get(CONF_SPOTIFY_PASSWORD)
                )
            )
        if conf.get(CONF_QOBUZ_ENABLED):
            await mass.music.register_provider(
                QobuzProvider(
                    conf.get(CONF_QOBUZ_USERNAME), conf.get(CONF_QOBUZ_PASSWORD)
                )
            )
        if conf.get(CONF_TUNEIN_ENABLED):
            await mass.music.register_provider(
                TuneInProvider(conf.get(CONF_TUNEIN_USERNAME))
            )
    except MusicAssistantError as err:
        raise ConfigEntryNotReady from err

    hass.data[DOMAIN] = mass

    # initialize platforms
    if conf.get(CONF_CREATE_MASS_PLAYERS):
        hass.config_entries.async_setup_platforms(
            entry, ("media_player", "switch", "number")
        )

    # register hass players with mass
    controls = HassPlayerControls(hass, mass, entry.options)
    hass.async_create_task(controls.async_register_player_controls())

    # register callbacks
    async def handle_mass_event(event: EventType, details: Any):
        """Handle an incoming event from Music Assistant."""
        if event == EventType.QUEUE_ADDED:
            async_dispatcher_send(hass, DISPATCH_KEY_QUEUE_ADDED, details)
            return
        if event == EventType.QUEUE_UPDATED:
            async_dispatcher_send(
                hass, f"{DISPATCH_KEY_QUEUE_UPDATE}_{details.queue_id}"
            )
            return

    async def handle_hass_event(event: Event):
        """Handle an incoming event from Home Assistant."""
        if event.event_type == EVENT_HOMEASSISTANT_STOP:
            await mass.stop()
        elif event.event_type == EVENT_CALL_SERVICE:
            await async_intercept_play_media(event, controls)

    entry.async_on_unload(mass.subscribe(handle_mass_event))
    entry.async_on_unload(entry.add_update_listener(_update_listener))
    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, handle_hass_event)
    )
    entry.async_on_unload(hass.bus.async_listen(EVENT_CALL_SERVICE, handle_hass_event))

    return True


async def _update_listener(hass: HomeAssistantType, entry: ConfigEntry) -> None:
    """Handle ConfigEntry options update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_remove_config_entry_device(
    hass: HomeAssistantType, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device."""
    return True


async def async_intercept_play_media(
    event: Event,
    controls: HassPlayerControls,
):
    """Intercept play_media service calls."""
    if event.data["domain"] != "media_player":
        return
    if event.data["service"] != "play_media":
        return
    entity_id = event.data["service_data"]["entity_id"]
    media_content_id = event.data["service_data"]["media_content_id"]

    if not media_content_id.startswith(f"media-source://{DOMAIN}/"):
        return

    uri = media_content_id.replace(f"media-source://{DOMAIN}/", "")

    # create player on the fly (or get existing one)
    player = await controls.async_register_player_control(entity_id, manual=True)
    if not player:
        return

    # send the mass library uri to the player(queue)
    await player.queue.play_media(uri)


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    if mass := hass.data.pop(DOMAIN):
        await mass.stop()
        del mass
    return True
