"""Run the client against an in-memory HTTP endpoint."""
from __future__ import annotations

import hashlib
import json
from collections import deque
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_history import load, privacy

api = load("api")
http = load("cloud_http")
HTTP_CONTRACT = json.loads((Path(__file__).parents[1] / "fixtures/2026.11.10.1-http-contract.json").read_text(encoding="utf-8"))


def session(token="first"):
    return {
        "token": {"token": token, "refreshToken": "refresh", "expireAt": 9999999999999},
        "user": {"userId": 42},
    }


@pytest.fixture
def client():
    return api.UbpetClient(
        account="demo@example.test", password="fixture-pass", app_key="fixture-app-key",
        device_id="fixture-install", base_url="https://eu.example.test", app_id="fixture-app",
        product="fixture-model", area_code="DE",
    )


@pytest.fixture
def server(monkeypatch):
    calls = []
    replies = deque()

    @contextmanager
    def accept(request, *, timeout):
        assert timeout > 0
        calls.append((
            request.get_method(), request.selector,
            json.loads(request.data) if request.data is not None else None,
            {name.lower(): value for name, value in request.header_items()},
        ))
        status, data = replies.popleft()
        yield SimpleNamespace(status=status, read=lambda: json.dumps(data).encode())

    monkeypatch.setattr(http.request, "urlopen", accept)
    return calls, replies


@pytest.mark.parametrize("wrapped", [True, False])
def test_login_reads_both_response_formats(client, server, wrapped):
    calls, replies = server
    reply = session()
    replies.append((200, {"code": 0, "data": reply} if wrapped else reply))
    auth = client.login()
    assert (auth.token, auth.user_id, auth.refresh_token) == ("first", 42, "refresh")
    verb, path, body, headers = calls[0]
    assert (verb, path) == ("PUT", "/user-service-rest/v2/user/login")
    assert body == {
        "account": "demo@example.test", "password": hashlib.md5(b"fixture-pass").hexdigest(),
        "accountType": "1", "areaCode": "DE",
    }
    assert "product" not in headers and "authorization" not in headers


@pytest.mark.parametrize(("account", "order"), [("a@example.test", ["1", "0"]), ("33123456", ["0", "1"])])
def test_account_type_fallback(client, server, account, order):
    calls, replies = server
    client.account = account
    replies.extend([(200, {"code": 2004}), (200, session())])
    assert client.login().token == "first"
    assert [call[2]["accountType"] for call in calls] == order


@pytest.mark.parametrize("second_status", [200, 401])
def test_only_one_retry_uses_a_fresh_token(client, server, second_status):
    calls, replies = server
    devices = [{"serialNumber": "fixture-box"}]
    replies.extend([(200, session()), (401, {}), (200, session("renewed")), (second_status, {"data": devices})])
    if second_status == 200:
        assert client.get_devices() == devices
    else:
        with pytest.raises(api.UbpetApiError) as rejected:
            client.get_devices()
        assert rejected.value.status == 401
    assert [call[3].get("authorization") for call in calls] == [None, "first", None, "renewed"]
    assert calls[1][1] == "/user-service-rest/v2/robot/common/device/list"
    device_headers = calls[1][3]
    assert device_headers["product"] == "fixture-model"
    assert device_headers["x-ubt-appid"] == "fixture-app"
    assert device_headers["x-ubt-deviceid"] == "fixture-install"
    assert device_headers["x-ubt-sign"].endswith(" v2")


_CONFIG = "/catbox-server/box/config/"
_SWITCH = _CONFIG + "switch/update"
_DEODORANT = "/catbox-server/app/deodorant-block/"
_IM = "/v1/ubtechinc-im-manager/im/"
_SERIAL = "fixture-box"


@pytest.mark.parametrize(("command", "args", "kwargs", "method", "path", "fields"), [
    ("set_auto_clean_delay", (10,), {}, "PUT", _SWITCH, {
        "functionType": 2, "controlSwitch": 1, "optionInt": 600,
    }),
    ("set_auto_clean_enabled", (False, 480), {}, "PUT", _SWITCH, {
        "functionType": 2, "controlSwitch": 0, "optionInt": 480,
    }),
    ("reset_box_use_times", (), {}, "PUT", _CONFIG + "box-use-times/reset", {"boxUseTimes": 0}),
    ("set_deodorant_alert", (True,), {}, "POST", _DEODORANT + "switch", {"alertSwitch": 1}),
    ("set_time_point", (), {
        "config_id": 8, "function_type": 1, "open_switch": 1, "time_hour": 19, "time_minute": 30, "option_int": 28,
    }, "PUT", _CONFIG + "timePoint/update", {
        "configId": 8, "functionType": 1, "openSwitch": 1, "timeHour": 19, "timeMinute": 30, "optionInt": 28,
    }),
    ("set_time_period", (), {
        "config_id": 9, "function_type": 1, "open_switch": 1,
        "start_hour": 23, "start_minute": 0, "end_hour": 6, "end_minute": 30,
    }, "PUT", _CONFIG + "timePeriod/update", {
        "configId": 9, "functionType": 1, "openSwitch": 1,
        "startTimeHour": 23, "startTimeMinute": 0, "endTimeHour": 6, "endTimeMinute": 30,
    }),
])
def test_configuration_write_contract(client, server, command, args, kwargs, method, path, fields):
    calls, replies = server
    replies.extend([(200, session()), (200, {"code": 0, "data": None})])
    getattr(client, command)(_SERIAL, *args, **kwargs)
    assert calls[1][:3] == (method, path, dict(fields, serialNumber=_SERIAL))


def test_visit_query_filters_non_records(client, server):
    calls, replies = server
    visit = {"eventType": 3, "eventTime": 1780553570000}
    replies.extend([(200, session()), (200, {"data": {"records": [visit, None]}})])
    assert client.get_box_records(_SERIAL, 0, 2) == [visit]
    assert calls[1][:3] == (
        "POST", "/catbox-server/web/box/record/new",
        {"eventTime": "0", "serialNumber": _SERIAL, "size": 2, "messageType": 0},
    )


def test_device_messaging_login_and_contacts(client, server):
    calls, replies = server
    credentials = {"clientId": "fixture-client", "subTopic": "fixture/in", "pubTopic": "fixture/out"}
    contacts = [{"userId": "fixture-uid", "userName": _SERIAL}]
    replies.extend([(200, session()), (200, {"data": credentials}), (200, {"data": contacts})])
    assert client.get_im_credentials() == credentials
    assert client.get_im_friends() == contacts
    assert calls[1][:3] == ("POST", _IM + "login", {"type": 2})
    assert calls[2][:3] == ("GET", _IM + "friends", None)


def test_signature_bytes(monkeypatch):
    monkeypatch.setattr(http.time, "time", lambda: 1234567890)
    monkeypatch.setattr(http.secrets, "choice", lambda _: "A")
    actual = http.HeaderSigner("app-key").header("device-id")
    expected = hashlib.md5(b"1234567890app-keyAAAAAAAAAAdevice-id").hexdigest()
    assert actual == expected + " 1234567890 AAAAAAAAAA v2"


@pytest.mark.parametrize("case", HTTP_CONTRACT["cases"], ids=lambda case: case["client_method"])
def test_http_requests_preserve_the_pre_rewrite_contract(case, monkeypatch):
    calls = []

    @contextmanager
    def respond(request, *, timeout):
        calls.append({"method": request.get_method(), "path": request.selector, "timeout": timeout,
                      "body": json.loads(request.data) if request.data is not None else None,
                      "headers": {key.lower(): value for key, value in request.header_items()}})
        yield SimpleNamespace(status=200, read=lambda: json.dumps({"code": 0, "data": case["reply_data"]}).encode())

    monkeypatch.setattr(http.request, "urlopen", respond)
    monkeypatch.setattr(http.time, "time", lambda: 1234567890)
    monkeypatch.setattr(http.secrets, "choice", lambda _: "A")
    client = api.UbpetClient(account="fixture@example.test", password="fixture-password", app_key="fixture-key",
                             device_id="fixture-device", base_url="https://fixture.example.test",
                             app_id="fixture-app", product="fixture-product")
    client.auth = api.UbpetAuth("fixture-token", None, None, 42)
    getattr(client, case["client_method"])(*case["args"], **case["kwargs"])
    assert calls == [case["request"]]


@pytest.mark.parametrize("expiry", [None, 0, ""])
def test_unknown_token_expiry_does_not_trigger_a_new_login_each_request(client, server, expiry):
    calls, replies = server
    payload = session()
    payload["token"]["expireAt"] = expiry
    replies.extend([(200, payload), (200, {"data": []}), (200, {"data": []})])
    client.login()
    assert client.get_devices() == client.get_devices() == []
    assert [call[0] for call in calls] == ["PUT", "GET", "GET"]


@pytest.mark.parametrize("user", [None, "unavailable", []])
def test_optional_user_profile_does_not_prevent_token_login(client, server, user):
    _, replies = server
    payload = session()
    payload["user"] = user
    replies.append((200, payload))
    assert client.login().user_id is None


def test_optional_failure_leaves_device_and_marks_section_stale(client, monkeypatch):
    client.auth = api.UbpetAuth("token", None, None, 42)
    fixtures = {
        "get_devices": [{"serialNumber": _SERIAL, "deviceName": "Box"}],
        "get_all_config": {"wifiName": "fixture-network"},
        "get_box_use_times": {"boxUseTimes": 10},
        "get_device_online": {"online": True},
        "get_cats": [{"catInfoId": 5, "nickname": "Cat"}],
        "get_box_records": [],
        "get_capabilities": {"values": []},
    }
    for method, value in fixtures.items():
        monkeypatch.setattr(client, method, lambda *_, result=value: result)

    def unavailable(_):
        raise api.UbpetApiError(500, {"code": 1})

    monkeypatch.setattr(client, "get_deodorant_status", unavailable)
    state = client.get_dashboard()
    box = state["devices"][_SERIAL]
    assert box["device"]["deviceName"] == "Box"
    assert box["config"]["wifiName"] == "fixture-network"
    assert box["deodorant"] == {} and not box["fresh"]["deodorant"]
    assert state["cats"][0]["nickname"] == "Cat"


@pytest.mark.parametrize(("shape", "wrong"), [(dict, []), (list, {})])
def test_reject_response_shape(client, server, shape, wrong):
    _, replies = server
    replies.extend([(200, session()), (200, {"data": wrong})])
    operation = client.get_im_credentials if shape is dict else client.get_devices
    with pytest.raises(api.UbpetApiError):
        operation()


def test_diagnostics_hide_identifiers_but_keep_firmware():
    clean = privacy.redact({
        "account": "person@example.test", "password": "fixture-secret", "device_id": "fixture-id",
        "config": {"wifiName": "fixture-network", "gmtTimeZone": "GMT+03:00", "firmwareVersion": "v1"},
        "cats": [{"nickname": "Cat", "icon": "https://private.example.test/cat.png"}],
    })
    assert {clean[k] for k in ("account", "password", "device_id")} == {"REDACTED"}
    assert clean["config"] == {"wifiName": "REDACTED", "gmtTimeZone": "GMT+03:00", "firmwareVersion": "v1"}
    assert clean["cats"] == [{"nickname": "REDACTED", "icon": "REDACTED"}]
