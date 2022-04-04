"""Support for switch platform for Music Assistant config options."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from music_assistant import MusicAssistant
from music_assistant.models.player_queue import PlayerQueue

from .const import  DISPATCH_KEY_QUEUE_ADDED, DOMAIN
from .entity import MassPlayerQueueEntityBase


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MusicAssistant switch platform."""
    mass: MusicAssistant = hass.data[DOMAIN]

    async def async_add_switch_entities(queue: PlayerQueue) -> None:
        """Add switch entities from Music Assistant PlayerQueue."""
        async_add_entities(
            [
                ShuffleEnabledEntity(mass, queue),
                RepeatEnabledEntity(mass, queue),
                NormalizeEnabledEntity(mass, queue),
            ]
        )

    # add all current items in controller
    for queue in mass.players.player_queues:
        await async_add_switch_entities(queue)

    # register listener for new queues
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            DISPATCH_KEY_QUEUE_ADDED,
            async_add_switch_entities,
        )
    )


class ShuffleEnabledEntity(MassPlayerQueueEntityBase, SwitchEntity):
    """Representation of a Switch entity to set shuffle enabled."""

    entity_description = SwitchEntityDescription(
        key="shuffle_enabled",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:shuffle",
        entity_category=EntityCategory.CONFIG,
        name="Shuffle enabled",
    )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.queue.shuffle_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_shuffle_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_shuffle_enabled(False)


class RepeatEnabledEntity(MassPlayerQueueEntityBase, SwitchEntity):
    """Representation of a Switch entity to set repeat enabled."""

    entity_description = SwitchEntityDescription(
        key="repeat_enabled",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:repeat",
        entity_category=EntityCategory.CONFIG,
        name="Repeat enabled",
    )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.queue.repeat_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_repeat_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_repeat_enabled(False)


class NormalizeEnabledEntity(MassPlayerQueueEntityBase, SwitchEntity):
    """Representation of a Switch entity to set volume normalization enabled."""

    entity_description = SwitchEntityDescription(
        key="normalize_enabled",
        device_class=SwitchDeviceClass.SWITCH,
        icon="mdi:chart-bar",
        entity_category=EntityCategory.CONFIG,
        name="Volume normalization enabled",
    )

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.queue.volume_normalization_enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_volume_normalization_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        await self.queue.set_volume_normalization_enabled(False)
