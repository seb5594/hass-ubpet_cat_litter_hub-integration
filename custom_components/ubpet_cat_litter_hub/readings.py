"""Project-owned projections from cloud snapshots to stable entity values.

Wire field names and registry suffixes are compatibility data. This module has
no Home Assistant or transport dependencies and never mutates a cloud snapshot.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from .box_config import empty_waste_bin_reminder_config, mask_days, mask_preset, reminder_mask
from .history import remaining_uses, timestamp, waste_full

BOX_FIELDS = {
    "box_use_times": ("box_use_times", "boxUseTimes"),
    "waste_bin_level": ("box_use_times", "percentage"),
    "box_full_max": ("box_use_times", "boxFullMax"),
    "box_full_alert": ("box_use_times", "boxFullAlert"),
    "deodorant_remaining_days": ("deodorant", "remainingDays"),
    "wifi_name": ("config", "wifiName"),
    "mqtt_work_mode": ("mqtt_state", "w_mode_app_name"),
    "mqtt_work_state": ("mqtt_state", "w_state_app_name"),
    "mqtt_work_cause": ("mqtt_state", "w_cause"),
    "visits_today": ("box_analytics", "visits_today"),
    "cleans_today": ("box_analytics", "cleans_today"),
    "last_clean": ("box_analytics", "last_clean"),
    "cleans_since_bin_reset": ("box_analytics", "cleans_since_bin_reset"),
    "last_used_by": ("box_analytics", "last_used_by"),
}
CAT_FIELDS = {
    "cat_weight": ("weight",), "cat_visits": ("number",), "cat_cost_time": ("costTime",),
    "cat_last_visit_duration": ("visit_analytics", "last_visit_duration_seconds"),
    "cat_pee_visits_24h": ("visit_analytics", "pee_visits_24h"),
    "cat_poo_visits_24h": ("visit_analytics", "poo_visits_24h"),
    "cat_last_pee": ("visit_analytics", "last_pee"),
    "cat_last_poo": ("visit_analytics", "last_poo"),
    "cat_last_visit": ("visit_analytics", "last_visit"),
    "cat_visits_24h": ("visit_analytics", "visits_24h"),
    "cat_duration_24h": ("visit_analytics", "duration_24h"),
    "cat_average_duration_24h": ("visit_analytics", "average_duration_24h"),
    "cat_maximum_duration_24h": ("visit_analytics", "maximum_duration_24h"),
    "cat_weight_change": ("visit_analytics", "weight_change"),
    "cat_visits_today": ("visit_analytics", "visits_today"),
    "cat_last_visit_weight": ("visit_analytics", "last_visit_weight"),
}
BINARY_FIELDS = {
    "online": ("online", "online"), "deodorant_expired": ("deodorant", "expired"),
    "sensor_switch": ("config", "sensorSwitch"), "camera_switch": ("config", "cameraSwitch"),
    "control_board_switch": ("config", "controlBoardSwitch"),
    "cat_inside": ("mqtt_state", "cat_inside"), "cat_nearby": ("mqtt_state", "foreign_state"),
    "cover_open": ("mqtt_state", "lid_state"), "drum_not_in_place": ("mqtt_state", "box_state"),
    "drum_stuck": ("mqtt_state", "motor_state"), "scale_fault": ("mqtt_state", "weigh_sensor"),
    "camera_fault": ("mqtt_state", "camera_state"), "light": ("mqtt_state", "led_state"),
    "firmware_updating": ("mqtt_state", "update_state"), "history_truncated": ("history_truncated",),
}


def at_path(snapshot, *path):
    """Missing, null and malformed groups all represent an unknown value."""
    node = snapshot
    for key in path:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def displayed_status(box):
    """A recognised live state takes precedence over the REST fallback."""
    live = at_path(box, "mqtt_state") or {}
    pair = (live.get("w_mode_app_name"), live.get("w_state_app_name"))
    if pair == ("IDLE", "RUNNING"):
        return "standby"
    statuses = {"PENDING": "standby", "RUNNING": "running", "PAUSED": "paused"}
    if pair[1] in statuses:
        return statuses[pair[1]]
    raw = at_path(box, "device", "deviceStatus")
    return {"1": "standby", "2": "running", "3": "paused"}.get(str(raw))


def module_versions(config):
    versions = []
    for component in at_path(config, "boxFunctionVOList") or ():
        release = at_path(component, "firmwareVersion")
        if isinstance(release, str) and release and release not in versions:
            versions.append(release)
    versions.sort()
    return ", ".join(versions) if versions else None


def box_reading(key, box, *, rest_at=None, mqtt_at=None):
    if key in BOX_FIELDS:
        return at_path(box, *BOX_FIELDS[key])
    if key == "box_status":
        return displayed_status(box)
    if key == "firmware_version":
        return module_versions(at_path(box, "config"))
    if key == "last_rest_update":
        return rest_at
    if key == "last_mqtt_update":
        return mqtt_at
    if key == "remaining_bin_uses":
        return remaining_uses(box)
    if key == "last_visit":
        return timestamp(at_path(box, "last_visit", "at"))
    if key == "mqtt_pet_position":
        presence = at_path(box, "mqtt_state", "cat_inside")
        return {True: "inside", False: "away"}.get(presence)
    if key == "empty_waste_bin_reminder_days":
        reminder = empty_waste_bin_reminder_config(at_path(box, "config") or {})
        return mask_preset(reminder_mask(reminder)) if reminder is not None else None
    if key == "scheduled_cleans":
        jobs = at_path(box, "config", "taskConfigList")
        return sum(at_path(job, "openSwitch") == 1 for job in jobs) if isinstance(jobs, list) else None
    if key == "auto_clean_delay_current":
        value = at_path(box, "config", "lazyTime")
        return value / 60 if isinstance(value, (float, int)) and not isinstance(value, bool) else None
    if key == "waste_bin_last_reset":
        value = at_path(box, "box_use_times", "boxUseTimesResetTime")
        try:
            seconds = float(value) / 1000
            return datetime.fromtimestamp(seconds, timezone.utc) if seconds > 0 else None
        except (TypeError, ValueError, OverflowError, OSError):
            return None
    raise KeyError(key)


def binary_reading(key, box, *, connected=False):
    if key == "mqtt_connected":
        return connected
    if key == "waste_bin_full":
        return waste_full(box)
    raw = at_path(box, *BINARY_FIELDS[key])
    if raw is None:
        return None
    if key == "drum_stuck":
        return raw in (1, 2, 3, 4)
    if key == "light":
        return isinstance(raw, (int, float)) and raw > 0
    if key in {"online", "deodorant_expired", "cat_inside", "history_truncated"}:
        return bool(raw)
    return raw == 1


def box_attributes(key, box, serial):
    attributes = {"serial_number": serial}
    if key == "last_visit":
        detail_paths = {
            "cat_name": ("box_analytics", "last_used_by"), "weight_kg": ("last_visit", "weight"),
            "duration_seconds": ("last_visit", "duration_seconds"),
        }
        attributes.update({name: value for name, path in detail_paths.items() if (value := at_path(box, *path)) is not None})
    elif key == "box_status":
        attributes.update(device_status_code=at_path(box, "device", "deviceStatus"),
                          mqtt_work_state=at_path(box, "mqtt_state", "w_state_app_name"))
    elif key in {"last_rest_update", "last_mqtt_update"}:
        attributes.update(at_path(box, "runtime_state") or {})
    elif key == "empty_waste_bin_reminder_days":
        reminder = empty_waste_bin_reminder_config(at_path(box, "config") or {})
        attributes["days"] = mask_days(reminder_mask(reminder or {}))
    elif key.startswith("mqtt_"):
        for field in ("w_mode", "w_state", "w_cause", "w_state_app_raw_name"):
            value = at_path(box, "mqtt_state", field)
            if value is not None:
                attributes[field] = value
    return attributes


def cat_attributes(profile, key, streams, threshold):
    relevant = [stream for name, stream in streams.items() if name.endswith(":cat_records")]
    attributes = dict(
        history_source="observed_vendor_records",
        history_complete_24h=bool(relevant) and all(stream.get("complete_24h", False) for stream in relevant),
        cat_info_id=profile.get("catInfoId"), nickname=profile.get("nickname"), picture=profile.get("icon"),
    )
    if key in ("cat_last_pee", "cat_last_poo", "cat_pee_visits_24h", "cat_poo_visits_24h"):
        attributes.update(classification="duration_estimate", threshold_seconds=threshold)
    return attributes
