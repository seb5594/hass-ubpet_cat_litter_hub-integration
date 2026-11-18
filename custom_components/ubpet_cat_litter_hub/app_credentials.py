"""Resolve application credentials from local entries without importing old code.

An app key is shared by an application profile, not tied to the user's login.
Only an unambiguous key for the exact origin, application and product is reused.
"""

from __future__ import annotations

from urllib.parse import urlsplit


def _profile(data):
    try:
        url = urlsplit(data.get("base_url", ""))
        application, product = data.get("app_id"), data.get("product")
        if (url.scheme != "https" or not url.hostname or url.username is not None or url.password is not None
                or url.query or url.fragment or not isinstance(application, str) or not application
                or not isinstance(product, str) or not product):
            return None
        port = 443 if url.port is None else url.port
        return url.hostname.casefold(), port, url.path.rstrip("/"), application, product
    except (TypeError, ValueError, AttributeError):
        return None


def reusable_app_key(target, saved_entries):
    """Return no key when a profile is incomplete or local candidates disagree."""
    identity = _profile(target)
    if identity is None:
        return None
    candidates = set()
    for saved in saved_entries:
        key = saved.get("app_key")
        if _profile(saved) == identity and isinstance(key, str) and key.strip():
            candidates.add(key)
    return next(iter(candidates)) if len(candidates) == 1 else None
