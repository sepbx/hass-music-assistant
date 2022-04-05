"""MediaPlayer platform for Music Assistant integration."""
from __future__ import annotations

from homeassistant.components import media_source
from homeassistant.components.media_player import BrowseMedia, MediaPlayerEntity
from homeassistant.components.media_player.const import (
    ATTR_MEDIA_ENQUEUE,
    SUPPORT_BROWSE_MEDIA,
    SUPPORT_CLEAR_PLAYLIST,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.dt import utcnow
from music_assistant import MusicAssistant
from music_assistant.helpers.images import get_image_url
from music_assistant.models.media_items import MediaType
from music_assistant.models.player_queue import PlayerQueue, QueueOption

from .const import DISPATCH_KEY_QUEUE_ADDED, DOMAIN
from .entity import MassPlayerQueueEntityBase

SUPPORTED_FEATURES = (
    SUPPORT_PAUSE
    | SUPPORT_VOLUME_SET
    | SUPPORT_STOP
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_NEXT_TRACK
    | SUPPORT_SHUFFLE_SET
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_PLAY
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_VOLUME_STEP
    | SUPPORT_CLEAR_PLAYLIST
    | SUPPORT_BROWSE_MEDIA
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Music Assistant MediaPlayer(s) from Config Entry."""
    mass: MusicAssistant = hass.data[DOMAIN]

    async def async_add_player(queue: PlayerQueue) -> None:
        """Add MediaPlayerEntity from Music Assistant PlayerQueue."""
        player = MassPlayer(mass, queue)
        async_add_entities([player])

    # add all current items in controller
    for queue in mass.players.player_queues:
        await async_add_player(queue)

    # register listener for new queues
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            DISPATCH_KEY_QUEUE_ADDED,
            async_add_player,
        )
    )


class MassPlayer(MassPlayerQueueEntityBase, MediaPlayerEntity):
    """Representation of MediaPlayerEntity from Music Assistant PlayerQueue."""

    def __init__(self, mass: MusicAssistant, queue: PlayerQueue) -> None:
        """Initialize MediaPlayer entity."""
        super().__init__(mass, queue)
        self.entity_id = f'media_player.mass_{queue.player_id.split(".")[-1]}'
        self._attr_supported_features = SUPPORTED_FEATURES
        self._attr_extra_state_attributes = {
            "is_mass_player": True,
            "is_group": queue.player.is_group,
        }
        if queue.player.is_group:
            self._attr_extra_state_attributes[
                ATTR_ENTITY_ID
            ] = queue.player.group_childs

    async def async_on_update(self) -> None:
        """Handle player updates."""
        self._attr_volume_level = self.queue.player.volume_level / 100
        self._attr_state = self.queue.player.state.value
        self._attr_shuffle = self.queue.shuffle_enabled
        self._attr_repeat = self.queue.repeat_enabled

        if current_item := self.queue.current_item:
            media_item = await self.mass.music.get_item_by_uri(current_item.uri)
            self._attr_media_duration = media_item.duration
            self._attr_media_position = self.queue.elapsed_time
            self._attr_media_position_updated_at = utcnow()
            self._attr_media_title = media_item.name
            self._attr_media_content_id = current_item.uri
            self._attr_media_image_url = await get_image_url(self.mass, media_item)
            if media_item.media_type == MediaType.TRACK:
                self._attr_media_content_type = "track"
                artists = ", ".join([x.name for x in media_item.artists])
                self._attr_media_artist = artists
                if media_item.album:
                    self._attr_media_album_name = media_item.album.name
                    self._attr_media_album_artist = media_item.album.artist.name
            else:
                self._attr_media_content_type = "radio"
        else:
            self._attr_media_duration = None
            self._attr_media_position = None
            self._attr_media_album_artist = None
            self._attr_media_album_name = None
            self._attr_media_title = None
            self._attr_media_content_id = None
            self._attr_media_content_type = None
            self._attr_media_image_url = None

    async def async_media_play(self) -> None:
        """Send play command to device."""
        await self.queue.play()

    async def async_media_pause(self) -> None:
        """Send pause command to device."""
        await self.queue.pause()

    async def async_media_stop(self) -> None:
        """Send stop command to device."""
        await self.queue.stop()

    async def async_media_next_track(self) -> None:
        """Send next track command to device."""
        await self.queue.next()

    async def async_media_previous_track(self) -> None:
        """Send previous track command to device."""
        await self.queue.previous()

    async def async_set_volume_level(self, volume: float) -> None:
        """Send new volume_level to device."""
        volume = int(volume * 100)
        await self.queue.player.volume_set(volume)

    async def async_volume_up(self):
        """Send new volume_level to device."""
        await self.queue.player.volume_up()

    async def async_volume_down(self):
        """Send new volume_level to device."""
        await self.queue.player.volume_down()

    async def async_turn_on(self):
        """Turn on device."""
        await self.queue.player.power(True)

    async def async_turn_off(self):
        """Turn off device."""
        await self.queue.player.power(False)

    async def async_set_shuffle(self, shuffle: bool):
        """Set shuffle state."""
        await self.queue.set_shuffle_enabled(shuffle)

    async def async_set_repeat(self, repeat: bool):
        """Set repeat state."""
        await self.queue.set_shuffle_enabled(repeat)

    async def async_clear_playlist(self):
        """Clear players playlist."""
        await self.queue.clear()

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Send the play_media command to the media player."""
        media_id = media_id.replace(f"media-source://{DOMAIN}/", "")
        queue_opt = (
            QueueOption.ADD if kwargs.get(ATTR_MEDIA_ENQUEUE) else QueueOption.PLAY
        )
        await self.queue.play_media(media_id, queue_opt)

    async def async_browse_media(
        self, media_content_type=None, media_content_id=None
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
            content_filter=lambda item: item.media_content_type.startswith("audio/")
            or item.media_content_type == DOMAIN,
        )
