"""Expose boolean settings through the shared read/plan/commit adapter.

Device selection, validation and network writes belong to the settings model,
not to separate switch implementations for each vendor function.
"""

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription

from .const import DOMAIN
from .entities import HubSettingEntity, setting_entities, setup_discovery


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]
    setup_discovery(account, entry, async_add_entities,
                    lambda: setting_entities(account, "switch", SwitchEntityDescription, SettingSwitch))


class SettingSwitch(HubSettingEntity, SwitchEntity):
    """Adapt the Home Assistant switch interface to one setting definition."""

    @property
    def is_on(self) -> bool | None:
        return self.setting_value

    async def async_turn_on(self, **kwargs) -> None:
        await self.async_change(True)

    async def async_turn_off(self, **kwargs) -> None:
        await self.async_change(False)
