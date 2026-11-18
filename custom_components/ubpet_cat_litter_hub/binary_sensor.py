"""Binary projections of the same snapshots used by ordinary measurements."""

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorEntityDescription

from .catalog import metric_descriptions
from .const import DOMAIN
from .entities import HubEntity, keep_or_supported, setup_discovery
from .readings import binary_reading

BINARY_SENSORS = tuple(description for _, description in metric_descriptions("binary_sensor", BinarySensorEntityDescription))


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]

    def discover_flags():
        for serial in (account.data or {}).get("devices", {}):
            for description in BINARY_SENSORS:
                if keep_or_supported(account, serial, description.key, "binary_sensor"):
                    yield MetricBinarySensor(account, "box", serial, description)

    setup_discovery(account, entry, async_add_entities, discover_flags)


class MetricBinarySensor(HubEntity, BinarySensorEntity):
    @property
    def is_on(self):
        if self.snapshot is None:
            return None
        return binary_reading(self.entity_description.key, self.snapshot, connected=self.coordinator.transport.connected)
