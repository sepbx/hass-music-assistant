"""Support for number platform for Music Assistant config options."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import TIME_SECONDS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from music_assistant import MusicAssistant
from music_assistant.models.player_queue import PlayerQueue

from .const import DISPATCH_KEY_QUEUE_ADDED, DOMAIN
from .entity import MassPlayerQueueEntityBase


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MusicAssistant number platform."""
    mass: MusicAssistant = hass.data[DOMAIN]

    async def async_add_number_entities(queue: PlayerQueue) -> None:
        """Add number entities from Music Assistant PlayerQueue."""
        async_add_entities(
            [
                CrossfadeDurationEntity(mass, queue),
                VolumeNormalizationTargetEntity(mass, queue),
            ]
        )

    # add all current items in controller
    for queue in mass.players.player_queues:
        await async_add_number_entities(queue)

    # register listener for new queues
    config_entry.async_on_unload(
        async_dispatcher_connect(
            hass,
            DISPATCH_KEY_QUEUE_ADDED,
            async_add_number_entities,
        )
    )


class CrossfadeDurationEntity(MassPlayerQueueEntityBase, NumberEntity):
    """Representation of a number entity to set the crossfade duration."""

    entity_description = NumberEntityDescription(
        key="crossfade_duration",
        icon="mdi:camera-timer",
        entity_category=EntityCategory.CONFIG,
        unit_of_measurement=TIME_SECONDS,
        name="Crossfade duration",
        max_value=10,
        min_value=0,
        step=1,
    )

    @property
    def value(self) -> bool:
        """Return current value."""
        return self.queue.crossfade_duration

    async def async_set_value(self, value: float) -> None:
        """Set new value."""
        await self.queue.set_crossfade_duration(int(value))


class VolumeNormalizationTargetEntity(MassPlayerQueueEntityBase, NumberEntity):
    """Representation of a number entity to set the volume normalization target."""

    entity_description = NumberEntityDescription(
        key="volume_normalization_target",
        icon="mdi:chart-bar",
        entity_category=EntityCategory.CONFIG,
        unit_of_measurement=TIME_SECONDS,
        name="Volume normalization target",
        max_value=0,
        min_value=-40,
        step=1,
    )

    @property
    def value(self) -> bool:
        """Return current value."""
        return self.queue.volume_normalization_target

    async def async_set_value(self, value: float) -> None:
        """Set new value."""
        await self.queue.set_volume_normalization_target(value)
