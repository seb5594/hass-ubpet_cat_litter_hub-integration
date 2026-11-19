"""Exercise every replacement switch against the frozen pre-rewrite commands."""

import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("homeassistant")
from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.exceptions import HomeAssistantError

from custom_components.ubpet_cat_litter_hub import cloud_http
from custom_components.ubpet_cat_litter_hub.api import UbpetApiError, UbpetAuth, UbpetClient
from custom_components.ubpet_cat_litter_hub.switch import SettingSwitch

FIXTURES = Path(__file__).parents[1] / "fixtures"
COMMANDS = json.loads((FIXTURES / "2026.11.10.1-switch-contract.json").read_text(encoding="utf-8"))["cases"]
DASHBOARD = json.loads((FIXTURES / "2026.11.10.1-entity-contract.json").read_text(encoding="utf-8"))["dashboard"]


def switch_entity(key):
    client = UbpetClient(account="fixture@example.test", password="fixture-password", app_key="fixture-key",
                         device_id="fixture-device", base_url="https://fixture.example.test",
                         app_id="fixture-app", product="fixture-product")
    client.auth = UbpetAuth("fixture-token", None, None, 42)
    account = SimpleNamespace(data=deepcopy(DASHBOARD), namespace="fixture-account", config_entry=None,
                              client=client, setting_locks={}, schedule_refresh=MagicMock(),
                              async_update_listeners=MagicMock())

    async def execute(method, *args):
        return method(*args)

    entity = SettingSwitch(account, "box", "fixture-box", SwitchEntityDescription(key=key))
    entity.hass = SimpleNamespace(async_add_executor_job=execute)
    return entity


@pytest.mark.parametrize("case", COMMANDS, ids=lambda case: case["key"] + ("-on" if case["enabled"] else "-off"))
async def test_every_switch_keeps_its_previous_wire_command(case, monkeypatch):
    calls = []

    @contextmanager
    def accept(request, *, timeout):
        calls.append({"method": request.get_method(), "path": request.selector, "body": json.loads(request.data)})
        yield SimpleNamespace(status=200, read=lambda: b'{"code":0,"data":null}')

    monkeypatch.setattr(cloud_http.request, "urlopen", accept)
    entity = switch_entity(case["key"])
    assert entity.is_on == case["initial_state"]
    await (entity.async_turn_on() if case["enabled"] else entity.async_turn_off())
    assert calls == [case["request"]]
    assert entity.is_on is case["enabled"]
    entity.coordinator.schedule_refresh.assert_called_once_with(15)


async def test_a_rejected_owner_setting_does_not_change_the_snapshot():
    entity = switch_entity("auto_clean")
    before = deepcopy(entity.coordinator.data)
    entity.hass.async_add_executor_job = AsyncMock(side_effect=UbpetApiError(403, {}))
    with pytest.raises(HomeAssistantError):
        await entity.async_turn_on()
    assert entity.coordinator.data == before
    entity.coordinator.schedule_refresh.assert_not_called()


async def test_a_failed_period_switch_does_not_overwrite_its_clock_values():
    entity = switch_entity("do_not_disturb")
    before = deepcopy(entity.coordinator.data)
    entity.hass.async_add_executor_job = AsyncMock(side_effect=OSError("offline"))
    with pytest.raises(HomeAssistantError):
        await entity.async_turn_off()
    assert entity.coordinator.data == before
