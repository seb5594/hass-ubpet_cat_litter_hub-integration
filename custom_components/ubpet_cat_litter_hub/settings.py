"""Plan validated setting changes without Home Assistant or network side effects."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time
from typing import Any

from .box_config import (
    REMINDER_PRESETS,
    WEEKDAY_BITS,
    empty_waste_bin_reminder_config,
    first_period_config,
    mask_preset,
    period_config_id,
    reminder_mask,
    seconds_to_minutes,
)
from .readings import at_path


@dataclass(frozen=True)
class Setting:
    key: str
    platform: str
    family: str
    label: str
    icon: str
    field: str = ""
    function: int = 0
    side: str = ""
    day_bit: int = 0

    def source(self, box):
        config = at_path(box, "config") or {}
        if self.family == "reminder":
            return empty_waste_bin_reminder_config(config)
        if self.family == "period":
            return first_period_config(config, self.field)
        if self.family == "deodorant":
            return at_path(box, "deodorant")
        if self.family == "capacity":
            return at_path(box, "box_use_times")
        if self.family == "notify":
            for notice in config.get("notifyConfigList") or ():
                if at_path(notice, "type") == self.function:
                    return notice
            return None
        return config

    def read(self, box):
        source = self.source(box)
        if not source:
            return None
        if self.platform == "time":
            prefix = self.side + "Time" if self.side else "time"
            try:
                return time(int(source[prefix + "Hour"]), int(source[prefix + "Minute"]))
            except (KeyError, TypeError, ValueError, OverflowError):
                return None
        if self.family == "reminder" and self.day_bit:
            return bool(reminder_mask(source) & self.day_bit)
        if self.platform == "select":
            preset = mask_preset(reminder_mask(source))
            return preset if preset in REMINDER_PRESETS else None
        field = "openSwitch" if self.family in {"period", "reminder", "notify"} else self.field
        raw = source.get(field)
        if self.platform == "switch":
            return None if raw is None else raw == 1
        if self.family == "auto":
            return seconds_to_minutes(raw)
        return raw


_BASE = (
    Setting("auto_clean", "switch", "auto", "Auto clean", "mdi:broom", "sensorSwitch", 2),
    Setting("auto_clean_delay", "number", "auto", "Auto clean delay", "mdi:broom", "lazyTime", 2),
    Setting("deodorant_alert", "switch", "deodorant", "Deodorant alert", "mdi:air-filter", "alertSwitch"),
    Setting("child_lock", "switch", "function", "Child lock", "mdi:lock", "controlBoardSwitch", 0),
    Setting("foreign_object_detection", "switch", "notify", "Foreign object detection", "mdi:motion-sensor", function=1),
    Setting("shake_mode", "switch", "function", "Shake mode", "mdi:shaker-outline", "litterType", 6),
    Setting("box_full_alert", "switch", "function", "Waste bin alert", "mdi:delete-alert", "boxFullAlertSwitch", 7),
    Setting("box_full_alert_threshold", "number", "capacity", "Waste bin full after", "mdi:delete-alert", "boxFullAlert"),
    Setting("empty_waste_bin_reminder", "switch", "reminder", "Empty waste bin reminder", "mdi:bell-ring-outline"),
    Setting("empty_waste_bin_reminder_time", "time", "reminder", "Empty waste bin reminder time", "mdi:bell-ring-outline"),
    Setting("empty_waste_bin_reminder_days_select", "select", "reminder", "Empty waste bin reminder days", "mdi:calendar-week"),
)
_PERIODS = (("do_not_disturb", "Do not disturb", "disturbTimeConfigList", 1, "mdi:minus-circle-outline"),
            ("light_schedule", "Light schedule", "lightTimeConfigList", 0, "mdi:lightbulb"))
SETTINGS = {setting.key: setting for setting in _BASE}
for key, label, field, function, icon in _PERIODS:
    SETTINGS[key] = Setting(key, "switch", "period", label, icon, field, function)
    for side in ("start", "end"):
        identity = key + "_" + side
        SETTINGS[identity] = Setting(identity, "time", "period", label + " " + side, icon, field, function, side)
for day, bit in WEEKDAY_BITS.items():
    SETTINGS["reminder_" + day] = Setting(
        "reminder_" + day, "switch", "reminder", day.capitalize(), "mdi:calendar-week", day_bit=bit,
    )


@dataclass(frozen=True)
class SettingWrite:
    setting: Setting
    method: str
    args: tuple
    kwargs: dict[str, Any]
    accepted_fields: dict[str, Any]

    def commit(self, box):
        """Update only fields accepted by REST, in the latest coordinator snapshot."""
        target = self.setting.source(box)
        if target is not None:
            target.update(self.accepted_fields)


def plan_setting(key, value, box):
    setting = SETTINGS[key]
    source = setting.source(box)
    if source is None:
        raise ValueError("The device has not supplied this setting")
    family = setting.family
    if family == "auto":
        if source.get("sensorSwitch") not in (0, 1) or source.get("lazyTime") is None:
            raise ValueError("Automatic cleaning settings are incomplete")
        if setting.platform == "number":
            if isinstance(value, bool) or value != int(value) or not 1 <= value <= 60:
                raise ValueError("Cleaning delay must be an integer from 1 to 60 minutes")
            args = (int(value), source["sensorSwitch"] == 1)
            method, changed = "set_auto_clean_delay", {"lazyTime": int(value) * 60}
        else:
            args = (bool(value), source["lazyTime"])
            method, changed = "set_auto_clean_enabled", {"sensorSwitch": int(value)}
        return SettingWrite(setting, method, args, {}, changed)
    if family in {"period", "reminder"}:
        return _schedule_write(setting, value, source)
    if family == "capacity":
        capacity = source.get("boxFullMax")
        if not isinstance(capacity, (float, int)) or isinstance(value, bool) or value != int(value) or not 1 <= value <= capacity:
            raise ValueError("Threshold must fit the reported bin capacity")
        return SettingWrite(setting, "set_box_full_alert", (int(value),), {}, {"boxFullAlert": int(value)})
    if family == "deodorant":
        return SettingWrite(setting, "set_deodorant_alert", (bool(value),), {}, {"alertSwitch": int(value)})
    field = "openSwitch" if family == "notify" else setting.field
    return SettingWrite(setting, "set_function_switch", (setting.function, bool(value)), {}, {field: int(value)})


def _schedule_write(setting, value, source):
    period = setting.family == "period"
    identity = period_config_id(source) if period else source.get("notifyConfigId")
    if identity is None:
        raise ValueError("The device has not supplied a schedule identifier")
    mapping = {"open_switch": "openSwitch"}
    if period:
        mapping.update(start_hour="startTimeHour", start_minute="startTimeMinute",
                       end_hour="endTimeHour", end_minute="endTimeMinute")
    else:
        mapping.update(time_hour="timeHour", time_minute="timeMinute", option_int="period")
    if any(source.get(field) is None for field in mapping.values()):
        raise ValueError("The device schedule is incomplete; refresh it before editing")
    fields = {argument: source[field] for argument, field in mapping.items()}
    if setting.platform == "time":
        prefix = setting.side + "_" if period else "time_"
        fields[prefix + "hour"], fields[prefix + "minute"] = value.hour, value.minute
    elif setting.platform == "select":
        fields["option_int"] = REMINDER_PRESETS[value]
    elif setting.day_bit:
        current = reminder_mask(source)
        fields["option_int"] = (current | setting.day_bit) if value else (current & ~setting.day_bit)
    else:
        fields["open_switch"] = int(value)
    accepted = {wire: fields[argument] for argument, wire in mapping.items()}
    fields.update(config_id=identity, function_type=setting.function if period else 1)
    return SettingWrite(setting, "set_time_period" if period else "set_time_point", (), fields, accepted)
