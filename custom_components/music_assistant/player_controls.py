"""Support Home Assistant media_player entities to be used as Players for Music Assistant."""
from __future__ import annotations
from typing import Dict, List

from homeassistant.components.cast.const import (
    CAST_MULTIZONE_MANAGER_KEY,
    DOMAIN as CAST_DOMAIN,
)
from homeassistant.components.media_player import DOMAIN as MP_DOMAIN
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_POSITION,
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_POSITION_UPDATED_AT,
)
from homeassistant.util.dt import utcnow
from homeassistant.components.media_player.const import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.components.media_player.const import (
    SERVICE_JOIN,
    SERVICE_PLAY_MEDIA,
    SERVICE_UNJOIN,
    SUPPORT_PLAY_MEDIA,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_SUPPORTED_FEATURES,
    EVENT_STATE_CHANGED,
    SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_PLAY,
    SERVICE_MEDIA_STOP,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    SERVICE_VOLUME_SET,
    STATE_OFF,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    STATE_ON,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_STANDBY,
    STATE_IDLE,
)
from homeassistant.helpers.event import Event
from homeassistant.helpers import entity_registry as er, device_registry as dr
from homeassistant.helpers.typing import HomeAssistantType
from music_assistant import MusicAssistant
from music_assistant.models.player import DeviceInfo, Player, PlayerState, PlayerGroup

from custom_components.music_assistant.const import CONF_PLAYER_ENTITIES, DOMAIN

OFF_STATES = [STATE_OFF, STATE_UNAVAILABLE, STATE_UNKNOWN, STATE_STANDBY]

STATE_MAPPING = {
    STATE_OFF: PlayerState.OFF,
    STATE_ON: PlayerState.IDLE,
    STATE_UNKNOWN: PlayerState.OFF,
    STATE_UNAVAILABLE: PlayerState.OFF,
    STATE_IDLE: PlayerState.IDLE,
    STATE_PLAYING: PlayerState.PLAYING,
    STATE_PAUSED: PlayerState.PAUSED,
    STATE_STANDBY: PlayerState.OFF,
}


class HassPlayer(Player):
    """Mapping from Home Assistant Mediaplayer to Music Assistant Player."""

    def __init__(self, hass: HomeAssistantType, entity_id: str) -> None:
        """Initialize player."""
        self.hass = hass
        self.player_id = entity_id
        self.is_group = False  # TODO
        self.entity_id = entity_id
        self.ent_reg = er.async_get(hass)

        manufacturer = "Home Assistant"
        model = entity_id
        if entry := self.ent_reg.async_get(self.entity_id):
            if entry.device_id:
                dev_reg = dr.async_get(hass)
                device = dev_reg.async_get(entry.device_id)
                manufacturer = device.manufacturer
                model = device.model
        self._attr_device_info = DeviceInfo(manufacturer=manufacturer, model=model)
        self.update()

    @property
    def elapsed_time(self) -> int:
        """Return elapsed time of current playing media in seconds."""
        if self._attr_state not in [PlayerState.PLAYING, PlayerState.PAUSED]:
            return 0
        # we need to return the corrected time here
        if state := self.hass.states.get(self.entity_id):
            elapsed_time = state.attributes.get(ATTR_MEDIA_POSITION, 0)
            last_upd = state.attributes.get(ATTR_MEDIA_POSITION_UPDATED_AT)
            diff = (utcnow() - last_upd).timestamp()
            return elapsed_time + diff

    def update(self) -> None:
        """Update state (properties)."""

        if state := self.hass.states.get(self.entity_id):
            self._attr_name = state.name
            self._attr_powered = state.state not in OFF_STATES
            self._attr_elapsed_time = state.attributes.get(ATTR_MEDIA_POSITION, 0)
            self._attr_current_url = state.attributes.get(ATTR_MEDIA_CONTENT_ID)
            self._attr_state = STATE_MAPPING.get(state.state, PlayerState.OFF)
            self._attr_available = state.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN]
            self._attr_current_url = state.attributes.get(ATTR_MEDIA_CONTENT_ID)
            self._attr_volume_level = int(
                state.attributes.get(ATTR_MEDIA_VOLUME_LEVEL, 0) * 100
            )
        else:
            self._attr_available = False

    async def play_url(self, url: str) -> None:
        """Play the specified url on the player."""
        await self.hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_MEDIA_CONTENT_TYPE: "music",
                ATTR_MEDIA_CONTENT_ID: url,
                "entity_id": self.entity_id,
            },
        )

    async def stop(self) -> None:
        """Send STOP command to player."""
        await self.hass.services.async_call(
            MP_DOMAIN, SERVICE_MEDIA_STOP, {"entity_id": self.entity_id}
        )

    async def play(self) -> None:
        """Send PLAY/UNPAUSE command to player."""
        await self.hass.services.async_call(
            MP_DOMAIN, SERVICE_MEDIA_PLAY, {"entity_id": self.entity_id}
        )

    async def pause(self) -> None:
        """Send PAUSE command to player."""
        await self.hass.services.async_call(
            MP_DOMAIN, SERVICE_MEDIA_PAUSE, {"entity_id": self.entity_id}
        )

    async def power(self, powered: bool) -> None:
        """Send POWER command to player."""
        cmd = SERVICE_TURN_ON if powered else SERVICE_TURN_OFF
        await self.hass.services.async_call(
            MP_DOMAIN, cmd, {"entity_id": self.entity_id}
        )

    async def volume_set(self, volume_level: int) -> None:
        """Send volume level (0..100) command to player."""
        await self.hass.services.async_call(
            MP_DOMAIN,
            SERVICE_VOLUME_SET,
            {"entity_id": self.entity_id, ATTR_MEDIA_VOLUME_LEVEL: volume_level / 100},
        )


class HassGroupPlayer(PlayerGroup, HassPlayer):
    """Mapping from Home Assistant Grouped Mediaplayer to Music Assistant Player."""

    def __init__(self, hass: HomeAssistantType, entity_id: str) -> None:
        """Initialize player."""
        super().__init__(hass, entity_id)
        self.is_group = True
        self._attr_support_join_control: bool = True
        self._attr_device_info = DeviceInfo(
            manufacturer="Home Assistant", model="Media Player Group"
        )

    @property
    def elapsed_time(self) -> int:
        """Return elapsed time of current playing media in seconds."""
        if self._attr_state not in [PlayerState.PLAYING, PlayerState.PAUSED]:
            return 0
        # grab details from first player that is powered
        for entity_id in self._attr_group_childs:
            player = self.mass.players.get_player(entity_id)
            if not player.powered:
                continue
            return player.elapsed_time

    @property
    def current_url(self) -> str:
        """Return url of current playing media."""
        if self._attr_state not in [PlayerState.PLAYING, PlayerState.PAUSED]:
            return ""
        # grab details from first player that is powered
        for entity_id in self._attr_group_childs:
            player = self.mass.players.get_player(entity_id)
            if not player.powered:
                continue
            return player.current_url

    def update(self) -> None:
        """Update state (properties)."""

        if state := self.hass.states.get(self.entity_id):
            self._attr_group_childs = state.attributes.get(ATTR_ENTITY_ID, [])
            self._attr_name = state.name
            self._attr_powered = state.state not in OFF_STATES
            self._attr_state = STATE_MAPPING.get(state.state, PlayerState.OFF)
            self._attr_available = state.state not in [STATE_UNAVAILABLE, STATE_UNKNOWN]

        else:
            self._attr_available = False

    async def play_url(self, url: str) -> None:
        """Play the specified url on the player."""
        # redirect command to all players that are powered on
        powered_players = []
        for entity_id in self._attr_group_childs:
            if child_state := self.hass.states.get(entity_id):
                if child_state.state in OFF_STATES:
                    continue
                powered_players.append(entity_id)
        # if all childs are on, send command to the parent player instead
        if len(powered_players) == len(self.group_childs):
            powered_players = self.entity_id

        await self.hass.services.async_call(
            MP_DOMAIN,
            SERVICE_PLAY_MEDIA,
            {
                ATTR_MEDIA_CONTENT_TYPE: "music",
                ATTR_MEDIA_CONTENT_ID: url,
                "entity_id": powered_players,
            },
        )


class HassCastGroupPlayer(PlayerGroup, HassPlayer):
    """Mapping from Google Cast GroupPlayer to Music Assistant Player."""

    def __init__(self, hass: HomeAssistantType, entity_id: str) -> None:
        """Initialize player."""
        self.ent_reg = er.async_get(hass)
        ent_entry = self.ent_reg.async_get(entity_id)
        self.cast_uuid = ent_entry.unique_id
        super().__init__(hass, entity_id)
        self.is_group = True
        self._attr_support_join_control: bool = False

    def update(self) -> None:
        """Update state (properties)."""
        super().update()
        # this is a bit hacky to get the group members
        # TODO: create PR to add these as stare aatributes to the cast integration
        mz_mgr = self.hass.data[CAST_MULTIZONE_MANAGER_KEY]
        if self.cast_uuid in mz_mgr._groups:
            mz_ctrl = mz_mgr._groups[self.cast_uuid]["listener"]._mz
            child_players = []
            for cast_uuid in mz_ctrl.members:
                if entity_id := self.ent_reg.entities.get_entity_id(
                    (MP_DOMAIN, CAST_DOMAIN, cast_uuid)
                ):
                    child_players.append(entity_id)
            self._attr_group_childs = child_players


class HassPlayerControls:
    """Enable Home Assisant entities to be used as Players for MusicAssistant."""

    def __init__(
        self, hass: HomeAssistantType, mass: MusicAssistant, config: dict
    ) -> None:
        """Initialize class."""
        self.hass = hass
        self.mass = mass
        self.config = config
        self._registered_players: Dict[str, HassPlayer] = {}

    async def async_hass_state_event(self, event: Event) -> None:
        """Handle hass state-changed events to update registered PlayerControls."""
        entity_id: str = event.data[ATTR_ENTITY_ID]

        if not entity_id.startswith(MP_DOMAIN):
            return

        if entity_id in self._registered_players:
            self._registered_players[entity_id].update()
            self._registered_players[entity_id].update_state()
        else:
            # entity not (yet) registered
            await self.async_register_player_control(entity_id)

    async def async_register_player_controls(self):
        """Register hass entities as player controls on Music Assistant."""

        for entity in self.hass.states.async_all(MEDIA_PLAYER_DOMAIN):
            await self.async_register_player_control(entity.entity_id)

        # subscribe to HomeAssistant state changed events
        self.hass.bus.async_listen(EVENT_STATE_CHANGED, self.async_hass_state_event)

    async def async_register_player_control(
        self, entity_id: str, manual=False
    ) -> HassPlayer | None:
        """Register hass entitie as player controls on Music Assistant."""
        if not manual and entity_id not in self.config.get(CONF_PLAYER_ENTITIES, []):
            return

        if entity_id in self._registered_players:
            return self._registered_players[entity_id]

        entity = self.hass.states.get(entity_id)
        if entity is None or entity.attributes is None:
            return

        if not (entity.attributes.get(ATTR_SUPPORTED_FEATURES, 0) & SUPPORT_PLAY_MEDIA):
            return

        ent_reg = er.async_get(self.hass)
        dev_reg = dr.async_get(self.hass)
        is_cast_group = False
        if ent_entry := ent_reg.async_get(entity_id):
            if ent_entry.platform == DOMAIN:
                # this is already a Music assistant player
                return
            if ent_entry.platform == CAST_DOMAIN:
                if dev_entry := dev_reg.async_get(ent_entry.device_id):
                    is_cast_group = dev_entry.model == "Google Cast Group"

        if is_cast_group:
            player = HassCastGroupPlayer(self.hass, entity_id)
        elif ATTR_ENTITY_ID in entity.attributes:
            player = HassGroupPlayer(self.hass, entity_id)
        else:
            player = HassPlayer(self.hass, entity_id)
        self._registered_players[entity_id] = player
        await self.mass.players.register_player(player)
        return player
