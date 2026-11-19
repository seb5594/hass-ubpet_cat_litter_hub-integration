"""Entity discovery and device identity shared across all platforms."""

from __future__ import annotations

import asyncio
from functools import partial

from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .compat import DeviceInfo, serial_info, translated_error
from .const import DOMAIN, MODEL_BOX, MODEL_CAT, entry_namespace
from .settings import SETTINGS, plan_setting
from .writes import async_write


class HubEntity(CoordinatorEntity):
    """Bind one platform description to a box or pet in one cloud account."""

    _attr_has_entity_name = True

    def __init__(self, account, subject, target_id, description, *, registry_key=None):
        super().__init__(account)
        self.subject = subject
        self.target_id = str(target_id)
        self.entity_description = description
        parts = [account.namespace]
        if subject == "cat":
            parts.append("cat")
        parts.extend((self.target_id, registry_key or description.key))
        self._attr_unique_id = "_".join(parts)

    @property
    def snapshot(self):
        data = self.coordinator.data or {}
        if self.subject == "box":
            return data.get("devices", {}).get(self.target_id)
        for profile in data.get("cats", []):
            if str(profile.get("catInfoId")) == self.target_id:
                return profile
        return None

    @property
    def available(self):
        return self.snapshot is not None and super().available

    @property
    def device_info(self):
        values = self.snapshot or {}
        pet = self.subject == "cat"
        identity = self.coordinator.cat_identifier(self.target_id) if pet else self.target_id
        name = values.get("nickname") if pet else values.get("device", {}).get("deviceName")
        info = DeviceInfo(
            name=name or self.target_id, model=MODEL_CAT if pet else MODEL_BOX,
            manufacturer=self.coordinator.provider_label, identifiers={(DOMAIN, identity)},
        )
        if not pet:
            info.update(serial_info(self.target_id))
        return info


class HubSettingEntity(HubEntity):
    """Execute a pure setting plan, serialised with other edits on the same box."""

    @property
    def setting(self):
        return SETTINGS[self.entity_description.key]

    @property
    def setting_value(self):
        return self.setting.read(self.snapshot)

    async def async_change(self, value):
        lock = self.coordinator.setting_locks.setdefault(self.target_id, asyncio.Lock())
        async with lock:
            try:
                command = plan_setting(self.entity_description.key, value, self.snapshot)
            except (KeyError, ValueError, TypeError) as error:
                raise translated_error("state_changed", "Settings are incomplete or changed; refresh the device") from error
            await async_write(self.hass, partial(
                getattr(self.coordinator.client, command.method), self.target_id, *command.args, **command.kwargs,
            ))
            command.commit(self.snapshot)
            self.coordinator.async_update_listeners()
            self.coordinator.schedule_refresh(15)


def setting_entities(account, platform, description_type, entity_type):
    """One discovery path for every writable box platform."""
    for setting in SETTINGS.values():
        if setting.platform != platform:
            continue
        metadata = dict(key=setting.key, translation_key=setting.key, name=setting.label,
                        icon=setting.icon, entity_category=EntityCategory.CONFIG)
        if setting.day_bit:
            metadata["entity_registry_enabled_default"] = False
        if platform == "number":
            delay = setting.family == "auto"
            metadata.update(native_min_value=1, native_max_value=60 if delay else 100, native_step=1)
            if delay:
                metadata["native_unit_of_measurement"] = "min"
        description = description_type(**metadata)
        for serial, box in (account.data or {}).get("devices", {}).items():
            known = er.async_get(account.hass).async_get_entity_id(platform, DOMAIN, f"{account.namespace}_{serial}_{setting.key}")
            required = setting.key in {"auto_clean", "deodorant_alert", "auto_clean_delay"}
            present = setting.source(box) is not None and supported(setting.key, box)
            if required or known or present and (platform == "select" or setting.read(box) is not None):
                yield entity_type(account, "box", serial, description)


def setup_discovery(coordinator, entry, adder, build):
    seen = set()
    previous = None

    @callback
    def discover():
        nonlocal previous
        data = coordinator.data or {}
        # Cheap fingerprint: entities depend on what the last REST refresh delivered and on which push
        # fields exist; hashing the whole config on every push would be wasted work.
        signature = (
            coordinator.last_rest_update_at,
            tuple(sorted((sn, len(item.get("mqtt_state", {}))) for sn, item in data.get("devices", {}).items())),
            tuple(sorted(str(cat.get("catInfoId")) for cat in data.get("cats", []))),
        )
        if signature == previous:
            return
        previous = signature
        new = []
        for entity in build():
            if entity.unique_id not in seen:
                seen.add(entity.unique_id)
                new.append(entity)
        if new:
            adder(new)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


def migrate_cat_devices(hass, entry):
    registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(registry, entry.entry_id):
        identifiers = set(device.identifiers)
        old = {
            (domain, key)
            for domain, key in identifiers
            if domain == DOMAIN and key.startswith("cat_") and key.count("_") == 1
        }
        if old and device.config_entries == {entry.entry_id}:
            identifiers.difference_update(old)
            identifiers.update((DOMAIN, f"cat_{entry_namespace(entry)}_{key[4:]}") for _, key in old)
            registry.async_update_device(device.id, new_identifiers=identifiers)


def supports_camera(item):
    caps = item.get("capabilities")
    if isinstance(caps, dict):
        return "cat_face_upload" in repr(caps.get("values"))
    return item.get("config", {}).get("cameraSwitch") is not None


def supported(key, item):
    if key in {"camera_switch", "camera_fault"}:
        return supports_camera(item)
    if key == "scheduled_cleans":
        return item.get("config", {}).get("taskConfigList") is not None
    if key in {"light", "light_schedule", "light_schedule_start", "light_schedule_end"}:
        return item.get("config", {}).get("lightSwitch") is not None
    return True


def keep_or_supported(coordinator, serial, key, platform):
    if supported(key, coordinator.data["devices"][serial]):
        return True
    registry = er.async_get(coordinator.hass)
    return registry.async_get_entity_id(platform, DOMAIN, f"{coordinator.namespace}_{serial}_{key}") is not None
