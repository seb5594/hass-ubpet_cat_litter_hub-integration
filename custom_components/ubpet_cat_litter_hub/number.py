"""Numeric cloud settings and a local duration-classification threshold."""

from homeassistant.components.number import NumberEntity, NumberEntityDescription, NumberMode
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN
from .entities import HubEntity, HubSettingEntity, setting_entities, setup_discovery
from .readings import at_path

_ESTIMATE_THRESHOLD = NumberEntityDescription(
    key="cat_poo_duration_threshold", translation_key="cat_poo_duration_threshold",
    name="Poo duration threshold (estimate)", icon="mdi:timer-cog-outline",
    native_min_value=10, native_max_value=150, native_step=1,
    native_unit_of_measurement="s", entity_category=EntityCategory.CONFIG,
)


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]

    def discover_numbers():
        yield from setting_entities(account, "number", NumberEntityDescription, SettingNumber)
        for profile in (account.data or {}).get("cats", []):
            if profile.get("catInfoId") is not None:
                yield EstimateThreshold(account, "cat", str(profile["catInfoId"]), _ESTIMATE_THRESHOLD,
                                        registry_key="poo_duration_threshold")

    setup_discovery(account, entry, async_add_entities, discover_numbers)


class SettingNumber(HubSettingEntity, NumberEntity):
    @property
    def mode(self):
        return NumberMode.SLIDER if self.setting.family == "auto" else NumberMode.BOX

    @property
    def native_max_value(self):
        if self.setting.family == "capacity":
            return at_path(self.snapshot, "box_use_times", "boxFullMax") or 100
        return self.entity_description.native_max_value

    @property
    def native_value(self):
        return self.setting_value

    async def async_set_native_value(self, value):
        await self.async_change(value)


class EstimateThreshold(HubEntity, NumberEntity):
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self):
        return self.coordinator.cat_poo_duration_threshold(self.target_id)

    async def async_set_native_value(self, value):
        await self.coordinator.async_set_cat_poo_duration_threshold(self.target_id, value)
