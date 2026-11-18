"""Signed HTTP exchange; independent of account policy and Home Assistant."""

from __future__ import annotations

import hashlib
import json
import secrets
import string
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

_PROFILE = json.loads(Path(__file__).with_name("http_profile.json").read_text(encoding="utf-8"))


class UbpetApiError(RuntimeError):
    def __init__(self, status: int, payload: Any):
        self.status, self.payload = status, payload
        code = payload.get("code") if isinstance(payload, dict) else None
        super().__init__(f"Cloud request rejected (HTTP {status}; code {code})")


class UbpetAuthenticationError(UbpetApiError):
    """Credentials must be corrected before further automatic attempts."""


@dataclass(slots=True)
class UbpetAuth:
    token: str
    refresh_token: str | None
    expires_at_ms: int | None
    user_id: int | str | None


@dataclass(frozen=True)
class Route:
    path: str
    method: str = "GET"
    shape: type | tuple[type, ...] | None = dict


def protocol_digest(value: str) -> str:
    """MD5 is mandated by this wire protocol, not used to store credentials."""
    return hashlib.md5(value.encode("utf-8"), usedforsecurity=False).hexdigest()


class HeaderSigner:
    def __init__(self, key):
        self._key = key

    def header(self, device_id):
        stamp = str(int(time.time()))
        nonce = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
        checksum = protocol_digest("".join((stamp, self._key, nonce, device_id)))
        return f"{checksum} {stamp} {nonce} v2"


class CloudHTTP:
    def __init__(self, origin, installation, application, product, key):
        self.origin = origin.rstrip("/")
        self.installation, self.application, self.product = installation, application, product
        self.signer = HeaderSigner(key)

    def exchange(self, route: Route, fields=None, *, token=None):
        headers = {**_PROFILE["headers"], "x-ubt-deviceid": self.installation,
                   "x-ubt-appid": self.application, "x-ubt-sign": self.signer.header(self.installation)}
        if token is not None:
            headers["authorization"], headers["product"] = token, self.product
        url = self.origin + route.path
        body = None
        if fields is not None:
            if route.method == "GET":
                url += "?" + parse.urlencode(fields, quote_via=parse.quote)
            else:
                body = json.dumps(fields, separators=(",", ":")).encode("utf-8")
        outgoing = request.Request(url, headers=headers, data=body, method=route.method)
        try:
            with request.urlopen(outgoing, timeout=_PROFILE["timeout_seconds"]) as incoming:
                status, raw = incoming.status, incoming.read()
        except error.HTTPError as failure:
            with failure:
                status, raw = failure.code, failure.read()
        try:
            envelope = json.loads(raw)
        except (ValueError, UnicodeError) as failure:
            raise UbpetApiError(status, {"code": "invalid_json"}) from failure
        code = envelope.get("code") if isinstance(envelope, dict) else None
        if status >= 400 or code not in (None, 0):
            raise UbpetApiError(status, envelope)
        return envelope


def response_data(envelope, shape):
    value = envelope.get("data") if isinstance(envelope, dict) else None
    if not isinstance(value, shape):
        raise UbpetApiError(200, {"code": "invalid_response_shape"})
    return value
