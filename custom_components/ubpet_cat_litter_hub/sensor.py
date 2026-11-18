"""Expose the measurement catalog through one account-scoped entity adapter."""

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription

from .catalog import metric_descriptions
from .const import DOMAIN
from .entities import HubEntity, keep_or_supported, setup_discovery
from .readings import CAT_FIELDS, at_path, box_attributes, box_reading, cat_attributes

_CATALOG = tuple(metric_descriptions("sensor", SensorEntityDescription))
DEVICE_SENSORS = tuple(description for subject, description in _CATALOG if subject == "box")
CAT_SENSORS = tuple(description for subject, description in _CATALOG if subject == "cat")


async def async_setup_entry(hass, entry, async_add_entities):
    account = hass.data[DOMAIN][entry.entry_id]

    def discover_measurements():
        for serial in (account.data or {}).get("devices", {}):
            for description in DEVICE_SENSORS:
                if keep_or_supported(account, serial, description.key, "sensor"):
                    yield MetricSensor(account, "box", serial, description)
        for cat in (account.data or {}).get("cats", []):
            if cat.get("catInfoId") is not None:
                for description in CAT_SENSORS:
                    yield MetricSensor(account, "cat", str(cat["catInfoId"]), description)

    setup_discovery(account, entry, async_add_entities, discover_measurements)


class MetricSensor(HubEntity, SensorEntity):
    @property
    def native_value(self):
        if self.snapshot is None:
            return None
        if self.subject == "cat":
            return at_path(self.snapshot, *CAT_FIELDS[self.entity_description.key])
        return box_reading(
            self.entity_description.key, self.snapshot,
            rest_at=self.coordinator.last_rest_update_at,
            mqtt_at=self.coordinator.last_mqtt_update_at(self.target_id),
        )

    @property
    def extra_state_attributes(self):
        if self.snapshot is None:
            return None
        key = self.entity_description.key
        if self.subject == "box":
            return box_attributes(key, self.snapshot, self.target_id)
        return cat_attributes(
            self.snapshot, key, self.coordinator.history.state["streams"],
            self.coordinator.cat_poo_duration_threshold(self.target_id),
        )
