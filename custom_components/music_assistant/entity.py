"""Base entity model."""
from __future__ import annotations

from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo, Entity
from music_assistant import MusicAssistant
from music_assistant.models.player_queue import PlayerQueue

from .const import (
    DEFAULT_NAME,
    DISPATCH_KEY_QUEUE_ADDED,
    DISPATCH_KEY_QUEUE_UPDATE,
    DOMAIN,
)


class MassPlayerQueueEntityBase(Entity):
    """Base Entity from Music Assistant PlayerQueue."""

    def __init__(self, mass: MusicAssistant, queue: PlayerQueue) -> None:
        """Initialize MediaPlayer entity."""
        self.mass = mass
        self.queue = queue
        self._attr_should_poll = False
        self._attr_unique_id = f"mass_{queue.queue_id}"
        self._attr_available = self.queue.available
        self._attr_name = self.queue.player.name
        dev_man = queue.player.device_info.manufacturer or DEFAULT_NAME
        dev_mod = queue.player.device_info.model or f"Queue {queue.player.name}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, queue.queue_id)},
            manufacturer=dev_man,
            model=dev_mod,
            name=self.queue.player.name,
        )

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        await self.async_on_update()
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DISPATCH_KEY_QUEUE_UPDATE}_{self.queue.queue_id}",
                self.__on_queue_update,
            )
        )

    @property
    def unique_id(self) -> str | None:
        """Return unique id for entity."""
        if hasattr(self, "entity_description"):
            return f"{self._attr_unique_id}_{self.entity_description.key}"
        return self._attr_unique_id

    @property
    def name(self) -> str | None:
        """Return default entity name."""
        if hasattr(self, "entity_description"):
            return f"{self._attr_name} {self.entity_description.name}"
        return self._attr_name

    async def __on_queue_update(self, *args, **kwargs):
        """Call when we receive queue update event."""
        self._attr_available = self.queue.available
        self._attr_name = self.queue.player.name
        await self.async_on_update()
        self.async_write_ha_state()

    async def async_on_update(self) -> None:
        """Handle player updates."""
