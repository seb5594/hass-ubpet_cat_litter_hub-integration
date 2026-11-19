"""Application keys can be reused locally without confusing cloud tenants."""

from copy import deepcopy

import pytest
from test_history import load

resolve = load("app_credentials").reusable_app_key
TARGET = {"base_url": "https://cloud.example.test", "app_id": "fixture-app", "product": "fixture-product"}


def test_different_accounts_can_share_an_exact_application_profile():
    entries = [{**TARGET, "account": "first@example.test", "app_key": "local-app-key", "password": "private"}]
    before = deepcopy(entries)
    assert resolve(TARGET, entries) == "local-app-key"
    assert entries == before


@pytest.mark.parametrize(("field", "value"), [
    ("base_url", "https://other.example.test"), ("base_url", "http://cloud.example.test"),
    ("base_url", "https://cloud.example.test:8443"), ("base_url", "https://cloud.example.test:0"),
    ("base_url", "https://cloud.example.test/another"),
    ("app_id", "other-app"), ("product", "other-product"),
])
def test_incompatible_profiles_do_not_supply_a_key(field, value):
    assert resolve(TARGET, [{**TARGET, "app_key": "local-app-key", field: value}]) is None


def test_url_normalization_does_not_change_the_case_of_paths():
    assert resolve(TARGET, [{**TARGET, "base_url": "https://CLOUD.example.test:443/", "app_key": "known"}]) == "known"
    assert resolve({**TARGET, "base_url": "https://cloud.example.test/Path"},
                   [{**TARGET, "base_url": "https://cloud.example.test/path", "app_key": "known"}]) is None


def test_conflicting_keys_are_not_chosen_by_entry_order():
    entries = [{**TARGET, "app_key": key} for key in ("old", "new")]
    assert resolve(TARGET, entries) is None
    assert resolve(TARGET, list(reversed(entries))) is None
    assert resolve(TARGET, [entries[0], entries[0]]) == "old"


@pytest.mark.parametrize("bad", [{"base_url": None}, {"app_id": 8}, {"product": None},
                                 {"base_url": "https://user:pass@cloud.example.test"},
                                 {"base_url": "https://cloud.example.test?token=private"},
                                 {"base_url": "https://cloud.example.test:invalid"}])
def test_missing_or_malformed_profiles_are_never_reused(bad):
    assert resolve({**TARGET, **bad}, [{**TARGET, "app_key": "known"}]) is None


def test_stored_key_bytes_are_not_normalized():
    assert resolve(TARGET, [{**TARGET, "app_key": " opaque key "}]) == " opaque key "
