"""Config flows use only compatible locally saved application keys."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytest.importorskip("homeassistant")
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME

from custom_components.ubpet_cat_litter_hub.config_flow import UbpetConfigFlow
from custom_components.ubpet_cat_litter_hub.const import DOMAIN, LEGACY_DOMAIN
from custom_components.ubpet_cat_litter_hub.providers import credentials, endpoint


def configured_flow(provider="upet", region="eu", saved_key="saved-app-key", saved_domain=DOMAIN):
    saved = SimpleNamespace(entry_id="previous", data={
        "account": "first@example.test", "password": "private-login", "app_key": saved_key,
        "base_url": endpoint(provider, region), **credentials(provider, region),
    })
    manager = SimpleNamespace(async_entries=lambda domain: [saved] if domain == saved_domain else [])
    flow = UbpetConfigFlow()
    flow.hass = SimpleNamespace(config_entries=manager, config=SimpleNamespace(country="DE", time_zone="Europe/Berlin"),
                                async_add_executor_job=AsyncMock(return_value=[]))
    flow._async_current_entries = MagicMock(return_value=[saved] if saved_domain == DOMAIN else [])
    flow.async_set_unique_id = AsyncMock()
    flow._abort_if_unique_id_configured = MagicMock()
    return flow


@pytest.mark.parametrize("domain", [DOMAIN, LEGACY_DOMAIN])
async def test_new_account_reuses_the_exact_local_profile_without_exposing_the_key(domain):
    flow = configured_flow(saved_domain=domain)
    form = await flow.async_step_account()
    key = next(field for field in form["data_schema"].schema if field.schema == "app_key")
    import voluptuous as vol
    assert isinstance(key, vol.Optional)
    assert key.default is vol.UNDEFINED
    result = await flow.async_step_account({"region": "eu", "country": "DE", CONF_USERNAME: "second@example.test",
                                            CONF_PASSWORD: "second-password"})
    assert result["type"] == "create_entry"
    assert result["data"]["app_key"] == "saved-app-key"
    assert result["data"]["password"] == "second-password"
    flow.hass.async_add_executor_job.assert_awaited_once()


@pytest.mark.parametrize(("provider", "region"), [("robotail", "eu"), ("upet", "na"), ("upet", "ru")])
async def test_other_profiles_cannot_supply_the_key(provider, region):
    flow = configured_flow()
    flow._provider = provider
    result = await flow.async_step_account({"region": region, "country": "DE", CONF_USERNAME: "second@example.test",
                                            CONF_PASSWORD: "second-password"})
    assert result["errors"] == {"app_key": "app_key_required"}
    flow.hass.async_add_executor_job.assert_not_awaited()


async def test_explicit_input_overrides_a_saved_application_key():
    flow = configured_flow()
    result = await flow.async_step_account({"region": "eu", "country": "DE", CONF_USERNAME: "second@example.test",
                                            CONF_PASSWORD: "second-password", "app_key": "replacement-key"})
    assert result["data"]["app_key"] == "replacement-key"


async def test_conflicting_local_keys_require_explicit_input_before_login():
    flow = configured_flow()
    first = flow.hass.config_entries.async_entries(DOMAIN)[0]
    conflict = SimpleNamespace(entry_id="conflict", data={**first.data, "app_key": "other-key"})
    with patch.object(flow.hass.config_entries, "async_entries", side_effect=lambda domain: [first, conflict] if domain == DOMAIN else []):
        result = await flow.async_step_account({"region": "eu", "country": "DE", CONF_USERNAME: "third@example.test",
                                                CONF_PASSWORD: "third-password"})
    assert result["errors"] == {"app_key": "app_key_required"}
    flow.hass.async_add_executor_job.assert_not_awaited()
