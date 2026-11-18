"""Account policy and endpoint adapter above the signed HTTP transport.

The public client surface is retained for the coordinator. Endpoint addresses,
field names and numeric options below describe the interoperability contract.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

from .cloud_http import (
    CloudHTTP,
    Route,
    UbpetApiError,
    UbpetAuth,
    UbpetAuthenticationError,
    protocol_digest,
    response_data,
)

_CONFIG_ROOT = "/catbox-server/box/config/"
_DEO_ROOT = "/catbox-server/app/deodorant-block/"
_MESSAGING_ROOT = "/v1/ubtechinc-im-manager/im/"
ROUTES = {
    "login": Route("/user-service-rest/v2/user/login", "PUT"),
    "devices": Route("/user-service-rest/v2/robot/common/device/list", shape=list),
    "cats": Route("/catbox-server/web/cat/info", shape=list),
    "configuration": Route(_CONFIG_ROOT + "allConfig"),
    "counter": Route(_CONFIG_ROOT + "box-use-times/"),
    "reset_counter": Route(_CONFIG_ROOT + "box-use-times/reset", "PUT", None),
    "bin_threshold": Route(_CONFIG_ROOT + "box-full-alert", "PUT", None),
    "deodorant": Route(_DEO_ROOT + "status"),
    "deodorant_switch": Route(_DEO_ROOT + "switch", "POST", None),
    "replace_deodorant": Route(_DEO_ROOT + "replaced", "POST", None),
    "online": Route(_MESSAGING_ROOT + "online/device/"),
    "messaging_login": Route(_MESSAGING_ROOT + "login", "POST"),
    "contacts": Route(_MESSAGING_ROOT + "friends", shape=list),
    "records": Route("/catbox-server/web/box/record/new", "POST"),
    "switch": Route(_CONFIG_ROOT + "switch/update", "PUT", None),
    "point": Route(_CONFIG_ROOT + "timePoint/update", "PUT", None),
    "period": Route(_CONFIG_ROOT + "timePeriod/update", "PUT", None),
    "capabilities": Route(_CONFIG_ROOT + "device/capabilities", shape=(dict, list)),
}
_WRONG_ACCOUNT_KIND = {1009, 2004, 2010, 2011, 2019, 2042}
_WRONG_CREDENTIALS = {2002, 2006, 2014, 2342}


class UbpetClient:
    def __init__(self, **connection):
        for field in ("account", "password", "app_id", "product", "device_id", "base_url"):
            setattr(self, field, connection[field])
        self.area_code = connection.get("area_code", "")
        self._http = CloudHTTP(self.base_url, self.device_id, self.app_id, self.product, connection["app_key"])
        self.auth = None
        self.auth_paused_until = 0.0
        self.records_per_fetch = 100
        self.mqtt_sender = None
        self._auth_lock = Lock()
        self._credential_failure = None
        self._section_values, self._unsupported_until = {}, {}

    def _guard_auth(self):
        if self._credential_failure is not None:
            raise self._credential_failure
        if self.auth_paused_until > time.monotonic():
            raise UbpetApiError(409, {"code": "session_in_use"})

    def _authenticate_kind(self, kind):
        envelope = self._http.exchange(ROUTES["login"], {
            "account": self.account, "password": protocol_digest(self.password),
            "accountType": kind, "areaCode": self.area_code,
        })
        payload = envelope.get("data", envelope) if isinstance(envelope, dict) else None
        if not isinstance(payload, dict) or not isinstance(payload.get("token"), dict):
            raise UbpetApiError(200, {"code": "missing_session"})
        details = payload["token"]
        if not isinstance(details.get("token"), str) or not details["token"]:
            raise UbpetApiError(200, {"code": "missing_token"})
        user = payload.get("user") or {}
        return UbpetAuth(details["token"], details.get("refreshToken"), details.get("expireAt"), user.get("userId"))

    def _new_session(self):
        kinds = ["1", "0", "2"] if "@" in self.account else ["0", "1", "2"]
        for index, kind in enumerate(kinds):
            try:
                self.auth = self._authenticate_kind(kind)
                return self.auth
            except UbpetApiError as failure:
                code = failure.payload.get("code") if isinstance(failure.payload, dict) else None
                terminal = failure.status in (401, 403) or code in _WRONG_CREDENTIALS
                fallback = not terminal and code in _WRONG_ACCOUNT_KIND and index + 1 < len(kinds)
                if fallback:
                    continue
                if terminal or code in _WRONG_ACCOUNT_KIND:
                    self._credential_failure = UbpetAuthenticationError(failure.status, failure.payload)
                    raise self._credential_failure from failure
                raise

    def _valid_session(self, rejected):
        if self.auth is None or self.auth.token == rejected:
            return False
        expiry = self.auth.expires_at_ms
        return expiry is None or float(expiry) > (time.time() + 300) * 1000

    def _access_session(self, rejected=None, force=False):
        with self._auth_lock:
            self._guard_auth()
            if not force and self._valid_session(rejected):
                return self.auth
            self.auth = None
            return self._new_session()

    def login(self):
        return self._access_session(force=True)

    def ensure_login(self):
        return self._access_session()

    def _invoke(self, operation, fields=None):
        route = ROUTES[operation]
        active = self.ensure_login()
        for attempt in range(2):
            try:
                envelope = self._http.exchange(route, fields, token=active.token)
            except UbpetApiError as failure:
                if failure.status != 401 or attempt:
                    raise
                active = self._access_session(rejected=active.token)
            else:
                return response_data(envelope, route.shape) if route.shape is not None else None

    def _device_write(self, operation, serial, **values):
        return self._invoke(operation, {"serialNumber": serial, **values})

    def get_devices(self):
        return self._invoke("devices")

    def get_cats(self):
        return self._invoke("cats")

    def get_all_config(self, serial_number):
        return self._invoke("configuration", {"serialNumber": serial_number})

    def get_box_use_times(self, serial_number):
        return self._invoke("counter", {"serialNumber": serial_number})

    def get_deodorant_status(self, serial_number):
        return self._invoke("deodorant", {"serialNumber": serial_number})

    def get_device_online(self, serial_number):
        return self._invoke("online", {"sn": serial_number})

    def get_capabilities(self, serial_number):
        return {"values": self._invoke("capabilities", {"sn": serial_number})}

    def get_im_credentials(self):
        return self._invoke("messaging_login", {"type": 2})

    def get_im_friends(self):
        return self._invoke("contacts")

    def get_box_records(self, serial_number, message_type, size=1):
        page = self._invoke("records", {"serialNumber": serial_number, "eventTime": "0",
                                        "messageType": message_type, "size": size})
        if "records" not in page or not isinstance(page["records"], (list, type(None))):
            raise UbpetApiError(200, {"code": "invalid_record_page"})
        return list(filter(lambda row: isinstance(row, dict), page["records"] or []))

    def reset_box_use_times(self, serial_number):
        self._device_write("reset_counter", serial_number, boxUseTimes=0)

    def reset_deodorant(self, serial_number):
        self._device_write("replace_deodorant", serial_number)

    def set_deodorant_alert(self, serial_number, enabled):
        self._device_write("deodorant_switch", serial_number, alertSwitch=int(enabled))

    def set_auto_clean_delay(self, serial_number, minutes, enabled=True):
        if isinstance(minutes, bool) or minutes != int(minutes) or not 1 <= minutes <= 60:
            raise ValueError("Invalid automatic cleaning delay")
        self._device_write("switch", serial_number, functionType=2, controlSwitch=int(enabled), optionInt=60 * int(minutes))

    def set_auto_clean_enabled(self, serial_number, enabled, lazy_time_seconds):
        if lazy_time_seconds is None:
            raise ValueError("Automatic cleaning delay is unknown")
        delay = lazy_time_seconds
        self._device_write("switch", serial_number, optionInt=delay, controlSwitch=int(enabled), functionType=2)

    def set_function_switch(self, serial_number, function_type, enabled):
        if function_type not in {0, 1, 6, 7}:
            raise ValueError("Unsupported switch function")
        self._device_write("switch", serial_number, optionInt=1, controlSwitch=int(enabled), functionType=function_type)

    def set_box_full_alert(self, serial_number, uses):
        if type(uses) is not int or uses < 1:
            raise ValueError("Invalid bin threshold")
        self._device_write("bin_threshold", serial_number, boxFullAlertTimes=uses)

    def set_time_point(self, serial_number, **fields):
        wire = {"configId": "config_id", "functionType": "function_type", "openSwitch": "open_switch",
                "timeHour": "time_hour", "timeMinute": "time_minute", "optionInt": "option_int"}
        self._device_write("point", serial_number, **{key: fields[arg] for key, arg in wire.items()})

    def set_time_period(self, serial_number, **fields):
        wire = {"configId": "config_id", "functionType": "function_type", "openSwitch": "open_switch",
                "startTimeHour": "start_hour", "startTimeMinute": "start_minute",
                "endTimeHour": "end_hour", "endTimeMinute": "end_minute"}
        self._device_write("period", serial_number, **{key: fields[arg] for key, arg in wire.items()})

    def send_mqtt_service(self, serial_number, service_id):
        if self.mqtt_sender is None:
            raise RuntimeError("Account messaging is not connected")
        return self.mqtt_sender(serial_number, service_id)

    def _optional(self, key, func, *args, default=None):
        fresh = False
        if time.monotonic() >= self._unsupported_until.get(key, 0):
            try:
                value = func(*args)
            except UbpetApiError as failure:
                if failure.status in {401, 403, 409} or isinstance(failure, UbpetAuthenticationError):
                    raise
                if failure.status in {404, 405}:
                    self._unsupported_until[key] = time.monotonic() + 3600
            except (OSError, RuntimeError):
                pass
            else:
                self._section_values[key] = value
                fresh = True
        return self._section_values.get(key, default), fresh

    def get_dashboard(self):
        self.ensure_login()
        sections = (
            ("config", self.get_all_config, (), {}), ("box_use_times", self.get_box_use_times, (), {}),
            ("deodorant", self.get_deodorant_status, (), {}), ("online", self.get_device_online, (), {}),
            ("cat_records", self.get_box_records, (0, self.records_per_fetch), []),
            ("device_records", self.get_box_records, (1, self.records_per_fetch), []),
            ("capabilities", self.get_capabilities, (), None),
        )
        dashboard = {"devices": {}, "user_id": self.auth.user_id if self.auth else None}
        boxes = dashboard["devices"]
        for device in self.get_devices():
            if isinstance(device, dict) and device.get("serialNumber"):
                boxes[device["serialNumber"]] = {"device": device, "fresh": {}}
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="litter-cloud") as pool:
            pending = {pool.submit(self._optional, "cats", self.get_cats, default=[]): (None, "cats")}
            for serial, box in boxes.items():
                for name, read, args, empty in sections:
                    identity = (serial, name)
                    if name == "capabilities" and identity in self._section_values:
                        box[name] = self._section_values[identity]
                        continue
                    pending[pool.submit(self._optional, identity, read, serial, *args, default=empty)] = (serial, name)
            for completed in as_completed(pending):
                serial, name = pending[completed]
                value, fresh = completed.result()
                if serial is None:
                    dashboard[name], dashboard["cats_fresh"] = value, fresh
                else:
                    boxes[serial][name], boxes[serial]["fresh"][name] = value, fresh
        return dashboard
