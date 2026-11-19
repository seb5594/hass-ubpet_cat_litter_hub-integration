"""Compare the replacement adapters with the released entity identity contract."""

import asyncio
import importlib
import json
from copy import deepcopy
from datetime import datetime, time, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")
from homeassistant.components.time import TimeEntityDescription
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubpet_cat_litter_hub.const import DOMAIN
from custom_components.ubpet_cat_litter_hub.entities import HubSettingEntity
from custom_components.ubpet_cat_litter_hub.sensor import DEVICE_SENSORS, MetricSensor

CONTRACT = json.loads((Path(__file__).parents[1] / "fixtures/2026.11.10.1-entity-contract.json").read_text(encoding="utf-8"))


def account():
    return SimpleNamespace(
        data=deepcopy(CONTRACT["dashboard"]), namespace="fixture-account", provider_label="Fixture",
        last_rest_update_at=datetime(2026, 11, 18, tzinfo=timezone.utc), last_mqtt_update_at=lambda serial: None,
        config_entry=None, last_update_success=True, hass=SimpleNamespace(),
        cat_identifier=lambda key: "cat_fixture-account_" + key, async_add_listener=MagicMock(),
        setting_locks={}, async_update_listeners=MagicMock(), schedule_refresh=MagicMock(),
        transport=SimpleNamespace(connected=False), history=SimpleNamespace(state={"streams": {}}),
        cat_poo_duration_threshold=lambda key: 100,
    )


async def test_all_released_entity_identities_and_statistics_metadata_survive():
    hub = account()
    entry = SimpleNamespace(entry_id=hub.namespace, async_on_unload=MagicMock())
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: hub}})
    entities = importlib.import_module("custom_components." + DOMAIN + ".entities")
    actual = {}
    with patch.object(entities.er, "async_get", return_value=SimpleNamespace(async_get_entity_id=lambda *args: None)):
        for platform in ("sensor", "binary_sensor", "switch", "number", "time", "select", "button"):
            added = []
            await importlib.import_module("custom_components." + DOMAIN + "." + platform).async_setup_entry(
                hass, entry, lambda values, added=added: added.extend(values),
            )
            for entity in added:
                identity = (platform, entity.unique_id)
                assert identity not in actual
                actual[identity] = entity
    expected = {(row["platform"], row["unique_id"]): row for row in CONTRACT["entities"]}
    assert actual.keys() == expected.keys()
    for identity, row in expected.items():
        for field, value in row.items():
            if field not in {"platform", "unique_id", "value_property", "expected_value", "expected_attributes"}:
                assert getattr(actual[identity].entity_description, field) == value, (identity, field)
        if "value_property" in row:
            value = getattr(actual[identity], row["value_property"])
            normalized = json.loads(json.dumps(value, default=lambda item: item.isoformat()))
            assert normalized == row["expected_value"], identity
        if "expected_attributes" in row:
            assert actual[identity].extra_state_attributes == row["expected_attributes"], identity


async def test_concurrent_period_edits_preserve_both_accepted_changes():
    hub = account()
    entered, finish = asyncio.Event(), asyncio.Event()
    calls = []

    async def execute(method):
        calls.append(method.keywords)
        if len(calls) == 1:
            entered.set()
            await finish.wait()

    hub.client = SimpleNamespace(set_time_period=MagicMock())
    first = HubSettingEntity(hub, "box", "fixture-box", TimeEntityDescription(key="do_not_disturb_start"))
    last = HubSettingEntity(hub, "box", "fixture-box", TimeEntityDescription(key="do_not_disturb_end"))
    first.hass = last.hass = SimpleNamespace(async_add_executor_job=execute)
    a = asyncio.create_task(first.async_change(time(23, 40)))
    await entered.wait()
    b = asyncio.create_task(last.async_change(time(7, 20)))
    await asyncio.sleep(0)
    assert len(calls) == 1
    finish.set()
    await asyncio.gather(a, b)
    assert calls[1]["start_hour"] == 23 and calls[1]["start_minute"] == 40
    assert calls[1]["end_hour"] == 7 and calls[1]["end_minute"] == 20


async def test_failed_write_leaves_the_snapshot_unchanged():
    hub = account()
    hub.client = SimpleNamespace(set_time_period=MagicMock())
    entity = HubSettingEntity(hub, "box", "fixture-box", TimeEntityDescription(key="do_not_disturb_start"))
    entity.hass = SimpleNamespace(async_add_executor_job=AsyncMock(side_effect=OSError("offline")))
    before = deepcopy(hub.data)
    with pytest.raises(HomeAssistantError):
        await entity.async_change(time(23, 40))
    assert hub.data == before
    hub.schedule_refresh.assert_not_called()


def test_disappeared_device_does_not_leave_a_measurement_exception():
    hub = account()
    entity = MetricSensor(hub, "box", "fixture-box", next(row for row in DEVICE_SENSORS if row.key == "remaining_bin_uses"))
    hub.data["devices"] = {}
    assert not entity.available
    assert entity.native_value is None
