"""Clock settings share the same schedule planner as switches and weekday presets."""

from homeassistant.components.time import TimeEntity, TimeEntityDescription

from .const import DOMAIN
from .entities import HubSettingEntity, setting_entities, setup_discovery


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]
    setup_discovery(account, entry, async_add_entities,
                    lambda: setting_entities(account, "time", TimeEntityDescription, ScheduleTime))


class ScheduleTime(HubSettingEntity, TimeEntity):
    @property
    def native_value(self):
        return self.setting_value

    async def async_set_value(self, value):
        await self.async_change(value)
