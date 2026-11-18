"""Specify setting behaviour without depending on Home Assistant platform classes."""

from copy import deepcopy
from datetime import time

import pytest
from test_history import load

settings = load("settings")
readings = load("readings")


@pytest.fixture
def box():
    return {"config": {
        "sensorSwitch": 0, "lazyTime": 120,
        "disturbTimeConfigList": [{"configId": 3, "openSwitch": 0, "startTimeHour": 22,
                                   "startTimeMinute": 15, "endTimeHour": 6, "endTimeMinute": 45}],
        "notifyConfigList": [{"type": 4, "notifyConfigId": 8, "openSwitch": 1,
                              "timeHour": 9, "timeMinute": 10, "period": 65}],
    }, "box_use_times": {"boxFullMax": 30, "boxFullAlert": 25}}


def test_planning_is_pure_and_preserves_disabled_auto_clean(box):
    before = deepcopy(box)
    plan = settings.plan_setting("auto_clean_delay", 7, box)
    assert (plan.method, plan.args, plan.kwargs) == ("set_auto_clean_delay", (7, False), {})
    assert box == before
    plan.commit(box)
    assert box["config"]["lazyTime"] == 420
    assert box["config"]["sensorSwitch"] == 0


def test_clock_change_preserves_other_boundary_and_disabled_schedule(box):
    plan = settings.plan_setting("do_not_disturb_start", time(23, 30), box)
    assert plan.method == "set_time_period"
    assert plan.kwargs == dict(config_id=3, function_type=1, open_switch=0,
                               start_hour=23, start_minute=30, end_hour=6, end_minute=45)
    plan.commit(box)
    assert settings.SETTINGS["do_not_disturb_start"].read(box) == time(23, 30)
    assert settings.SETTINGS["do_not_disturb"].read(box) is False


def test_weekday_edits_combine_using_the_last_accepted_mask(box):
    tuesday = settings.plan_setting("reminder_tuesday", True, box)
    assert tuesday.kwargs["option_int"] == 67
    tuesday.commit(box)
    monday = settings.plan_setting("reminder_monday", False, box)
    assert monday.kwargs == dict(config_id=8, function_type=1, open_switch=1,
                                 time_hour=9, time_minute=10, option_int=66)


@pytest.mark.parametrize("value", [0, -1, 61, 2.5, True, float("nan"), float("inf")])
def test_invalid_delays_do_not_produce_cloud_writes(box, value):
    with pytest.raises((ValueError, OverflowError)):
        settings.plan_setting("auto_clean_delay", value, box)


@pytest.mark.parametrize("value", [0, 31, 1.5, False])
def test_bin_threshold_cannot_exceed_device_capacity(box, value):
    with pytest.raises(ValueError):
        settings.plan_setting("box_full_alert_threshold", value, box)


def test_incomplete_period_is_not_overwritten_with_guessed_midnight(box):
    del box["config"]["disturbTimeConfigList"][0]["endTimeHour"]
    with pytest.raises(ValueError, match="incomplete"):
        settings.plan_setting("do_not_disturb_start", time(23, 30), box)
    assert settings.SETTINGS["do_not_disturb_end"].read(box) is None


def test_unknown_status_codes_do_not_pretend_to_mean_running():
    assert readings.displayed_status({"device": {"deviceStatus": 999}}) is None
    assert readings.displayed_status({"device": {"deviceStatus": "3"}}) == "paused"
    assert readings.displayed_status({"device": {"deviceStatus": 2}}) == "running"


def test_versions_are_stable_and_malformed_modules_are_ignored():
    assert readings.module_versions({"boxFunctionVOList": [None, {}, {"firmwareVersion": "b"},
                                                          {"firmwareVersion": "a"}, {"firmwareVersion": "b"}]}) == "a, b"


def test_device_only_streams_cannot_claim_complete_pet_history():
    assert not readings.cat_attributes({}, "cat_weight", {"box:device_records": {"complete_24h": True}}, 100)["history_complete_24h"]
