"""Expose reminder presets through the shared settings model."""

from homeassistant.components.select import SelectEntity, SelectEntityDescription

from .box_config import REMINDER_PRESETS
from .const import DOMAIN
from .entities import HubSettingEntity, setting_entities, setup_discovery


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]
    setup_discovery(account, entry, async_add_entities,
                    lambda: setting_entities(account, "select", SelectEntityDescription, ReminderSelect))


class ReminderSelect(HubSettingEntity, SelectEntity):
    _attr_options = list(REMINDER_PRESETS)

    @property
    def current_option(self):
        return self.setting_value

    async def async_select_option(self, option):
        await self.async_change(option)
