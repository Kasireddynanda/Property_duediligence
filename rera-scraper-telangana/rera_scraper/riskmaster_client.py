"""RiskMaster GraphQL client: Login -> OTP -> createWishlistv2."""

from __future__ import annotations

import copy
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("rera.riskmaster")

LOGIN_MUTATION = """
mutation Login($username: String!, $password: String!, $appId: Int) {
  login(username: $username, password: $password, appId: $appId) {
    message
    code
    sessionID
    __typename
  }
}
""".strip()

OTP_MUTATION = """
mutation OTP($otp: String!, $sessionID: String!, $appId: Int) {
  otp(otp: $otp, sessionID: $sessionID, appId: $appId) {
    message
    code
    token
    userDetails {
      username
      firstName
      lastName
      email
      __typename
    }
    __typename
  }
}
""".strip()

CREATE_WISHLISTV2_MUTATION = """
mutation createWishlistv2($name: String!, $org_id: Int!, $cps: WCPInputV2!, $company_id: Int!, $department_id: Int!) {
  createWishlistV2(
    name: $name
    org_id: $org_id
    cps: $cps
    company_id: $company_id
    department_id: $department_id
  ) {
    id
    name
    slug
    org_id
    company_id
    department_id
    created_at
    updated_at
    __typename
  }
}
""".strip()


def _verbose_logging() -> bool:
    return os.getenv("RISKMASTER_VERBOSE", "true").lower() in {"1", "true", "yes"}


def _json_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _redact_value(key: str, value: Any) -> Any:
    key_lower = key.lower()
    if key_lower in {"password", "otp", "token", "auth_token"}:
        text = str(value)
        if len(text) <= 4:
            return "***"
        return f"{text[:4]}...{text[-4:]} (len={len(text)})"
    if key_lower == "sessionid":
        text = str(value)
        return f"{text[:8]}...{text[-4:]} (len={len(text)})"
    return value


def _redact_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = copy.deepcopy(payload)
    variables = redacted.get("variables")
    if isinstance(variables, dict):
        for key, value in list(variables.items()):
            variables[key] = _redact_value(key, value)
    return redacted


def _redact_response(parsed: dict[str, Any]) -> dict[str, Any]:
    redacted = copy.deepcopy(parsed)
    data = redacted.get("data")
    if not isinstance(data, dict):
        return redacted

    login = data.get("login")
    if isinstance(login, dict) and login.get("sessionID"):
        login["sessionID"] = _redact_value("sessionID", login["sessionID"])

    otp = data.get("otp")
    if isinstance(otp, dict) and otp.get("token"):
        otp["token"] = _redact_value("token", otp["token"])

    return redacted


def _log_step(step: str, message: str, *, payload: Any = None, response: Any = None) -> None:
    logger.info("=== RiskMaster [%s] %s ===", step, message)
    if payload is not None:
        logger.info("[%s] REQUEST PAYLOAD:\n%s", step, _json_pretty(payload))
    if response is not None:
        logger.info("[%s] RESPONSE:\n%s", step, _json_pretty(response))


def _api_url() -> str:
    return os.getenv("RISKMASTER_API_URL", "https://api.riskmaster.signalx.ai/query")


def _app_id() -> int:
    return int(os.getenv("RISKMASTER_APP_ID", "4"))


def _default_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Accept": "application/graphql-response+json, application/graphql+json, application/json, text/event-stream",
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        ),
        "Referer": os.getenv("RISKMASTER_REFERER", "https://riskmaster.signalx.ai/"),
    }


def _graphql_request(
    payload: dict[str, Any],
    *,
    operation: str,
    auth_token: str | None = None,
    debug_trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    headers = _default_headers()
    if auth_token:
        headers["Cookie"] = f"auth_token={auth_token}"
        if _verbose_logging():
            logger.info(
                "[%s] Using auth_token cookie: %s",
                operation,
                _redact_value("auth_token", auth_token),
            )

    body = json.dumps(payload).encode("utf-8")
    redacted_payload = _redact_payload(payload)
    _log_step(operation, f"POST {_api_url()}", payload=redacted_payload)

    request = urllib.request.Request(
        _api_url(),
        data=body,
        headers=headers,
        method="POST",
    )

    step_record: dict[str, Any] = {
        "operation": operation,
        "url": _api_url(),
        "request": redacted_payload,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            status = getattr(response, "status", 200)
            raw = response.read().decode("utf-8")
            step_record["http_status"] = status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        step_record["http_status"] = exc.code
        step_record["error"] = detail
        _log_step(operation, f"HTTP ERROR {exc.code}", response={"raw": detail})
        if debug_trace is not None:
            debug_trace.append(step_record)
        raise _fail(
            f"RiskMaster API HTTP {exc.code}: {detail}",
            debug_trace=debug_trace or [],
        ) from exc
    except urllib.error.URLError as exc:
        step_record["error"] = str(exc)
        logger.error("[%s] URL ERROR: %s", operation, exc)
        if debug_trace is not None:
            debug_trace.append(step_record)
        raise _fail(
            f"RiskMaster API request failed: {exc}",
            debug_trace=debug_trace or [],
        ) from exc

    step_record["raw_response"] = raw
    if _verbose_logging():
        logger.info("[%s] RAW RESPONSE BODY:\n%s", operation, raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        step_record["error"] = f"Invalid JSON: {raw[:1000]}"
        _log_step(operation, "INVALID JSON RESPONSE", response={"raw": raw[:2000]})
        if debug_trace is not None:
            debug_trace.append(step_record)
        raise _fail(
            f"RiskMaster API returned invalid JSON: {raw[:500]}",
            debug_trace=debug_trace or [],
        ) from exc

    redacted_response = _redact_response(parsed)
    step_record["response"] = redacted_response
    _log_step(operation, "PARSED RESPONSE", response=redacted_response)

    if debug_trace is not None:
        debug_trace.append(step_record)

    if parsed.get("errors"):
        messages = "; ".join(
            err.get("message", str(err)) for err in parsed.get("errors", [])
        )
        logger.error("[%s] GraphQL errors: %s", operation, _json_pretty(parsed.get("errors")))
        raise _fail(
            f"RiskMaster GraphQL error: {messages}",
            debug_trace=debug_trace or [],
        )

    return parsed


class RiskMasterError(RuntimeError):
    def __init__(self, message: str, *, debug_trace: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.debug_trace = debug_trace or []


def _fail(
    message: str,
    *,
    debug_trace: list[dict[str, Any]],
    **extra: Any,
) -> RiskMasterError:
    logger.error("=== RiskMaster WISHLIST FLOW FAILED === %s", message)
    if debug_trace:
        logger.error("DEBUG TRACE:\n%s", _json_pretty(debug_trace))
    return RiskMasterError(message, debug_trace=debug_trace)


def _pan_from_gstin(gstin: str) -> str:
    gstin = gstin.strip().upper()
    if len(gstin) >= 12:
        return gstin[2:12]
    return ""


def normalize_pan(pan: str | None, gstin: str | None = None) -> str:
    pan = (pan or "").strip().upper()
    if pan:
        return pan
    if gstin:
        return _pan_from_gstin(gstin)
    return ""


def normalize_gstin(gstin: str | None) -> str:
    return (gstin or "").strip().upper()


def riskmaster_configured() -> bool:
    if os.getenv("RISKMASTER_AUTH_TOKEN", "").strip():
        return True
    return bool(
        os.getenv("RISKMASTER_USERNAME")
        and os.getenv("RISKMASTER_PASSWORD")
        and os.getenv("RISKMASTER_OTP")
    )


def build_group_name() -> str:
    now = datetime.now(UTC).astimezone()
    return f"Group-{now.strftime('%d%m%Y%H%M')}"


def login_riskmaster(debug_trace: list[dict[str, Any]] | None = None) -> str:
    """Step 1: Login and return sessionID."""
    username = os.getenv("RISKMASTER_USERNAME", "").strip()
    password = os.getenv("RISKMASTER_PASSWORD", "").strip()
    if not username or not password:
        raise RuntimeError("Set RISKMASTER_USERNAME and RISKMASTER_PASSWORD")

    payload = {
        "operationName": "Login",
        "query": LOGIN_MUTATION,
        "variables": {
            "appId": _app_id(),
            "password": password,
            "username": username,
        },
    }
    parsed = _graphql_request(payload, operation="Login", debug_trace=debug_trace)
    login_data = (parsed.get("data") or {}).get("login") or {}
    session_id = login_data.get("sessionID")
    logger.info(
        "[%s] login code=%s message=%s sessionID=%s",
        "Login",
        login_data.get("code"),
        login_data.get("message"),
        _redact_value("sessionID", session_id) if session_id else None,
    )
    if not session_id:
        raise _fail(
            f"RiskMaster login failed: {_json_pretty(parsed)}",
            debug_trace=debug_trace or [],
        )
    return str(session_id)


def verify_otp_riskmaster(
    session_id: str,
    debug_trace: list[dict[str, Any]] | None = None,
) -> str:
    """Step 2: Verify OTP and return auth token."""
    otp = os.getenv("RISKMASTER_OTP", "").strip()
    if not otp:
        raise RuntimeError("Set RISKMASTER_OTP")

    payload = {
        "operationName": "OTP",
        "query": OTP_MUTATION,
        "variables": {
            "appId": _app_id(),
            "otp": otp,
            "sessionID": session_id,
        },
    }
    parsed = _graphql_request(payload, operation="OTP", debug_trace=debug_trace)
    otp_data = (parsed.get("data") or {}).get("otp") or {}
    token = otp_data.get("token")
    logger.info(
        "[%s] otp code=%s message=%s token=%s",
        "OTP",
        otp_data.get("code"),
        otp_data.get("message"),
        _redact_value("token", token) if token else None,
    )
    if not token:
        raise _fail(
            f"RiskMaster OTP verification failed: {_json_pretty(parsed)}",
            debug_trace=debug_trace or [],
        )
    return str(token)


def authenticate_riskmaster(debug_trace: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Login -> OTP and return auth details."""
    static_token = os.getenv("RISKMASTER_AUTH_TOKEN", "").strip()
    if static_token:
        logger.info("RiskMaster auth: using static RISKMASTER_AUTH_TOKEN")
        return {"auth_token": static_token, "auth_method": "static_token"}

    logger.info("RiskMaster auth: starting Login -> OTP flow")
    session_id = login_riskmaster(debug_trace=debug_trace)
    token = verify_otp_riskmaster(session_id, debug_trace=debug_trace)
    return {
        "auth_token": token,
        "auth_method": "login_otp",
        "session_id": session_id,
    }


def build_create_wishlist_payload(
    *,
    promoter_name: str,
    pan: str,
    gstin: str | None = None,
    group_name: str | None = None,
    org_id: int | None = None,
    company_id: int | None = None,
    department_id: int | None = None,
) -> dict[str, Any]:
    promoter_name = promoter_name.strip()
    if not promoter_name:
        raise ValueError("promoter_name is required")

    pan = normalize_pan(pan, gstin)
    if not pan:
        raise ValueError("PAN is required for RiskMaster wishlist creation")

    gstin = normalize_gstin(gstin)
    gstins = [gstin] if gstin else []

    return {
        "operationName": "createWishlistv2",
        "query": CREATE_WISHLISTV2_MUTATION,
        "variables": {
            "company_id": company_id or int(os.getenv("RISKMASTER_COMPANY_ID", "144")),
            "department_id": department_id or int(os.getenv("RISKMASTER_DEPARTMENT_ID", "87")),
            "name": group_name or build_group_name(),
            "org_id": org_id or int(os.getenv("RISKMASTER_ORG_ID", "44")),
            "cps": {
                "non_companies": [
                    {
                        "country": "INDIA",
                        "identifiers": {
                            "india": {
                                "establishment_ids": [],
                                "gstins": gstins,
                                "pan": pan,
                            }
                        },
                        "name": promoter_name,
                        "report_id": "",
                        "status": "pending",
                    }
                ]
            },
        },
    }


def create_promoter_wishlist(
    *,
    promoter_name: str,
    pan: str,
    gstin: str | None = None,
    group_name: str | None = None,
) -> dict[str, Any]:
    """Authenticate (Login -> OTP) then create a RiskMaster wishlist."""
    debug_trace: list[dict[str, Any]] = []

    logger.info(
        "=== RiskMaster WISHLIST FLOW START === promoter=%r pan=%s gstin=%s",
        promoter_name,
        pan,
        gstin or "N/A",
    )

    if not riskmaster_configured():
        raise RuntimeError(
            "RiskMaster is not configured. Set RISKMASTER_USERNAME, "
            "RISKMASTER_PASSWORD, and RISKMASTER_OTP (or RISKMASTER_AUTH_TOKEN)."
        )

    auth = authenticate_riskmaster(debug_trace=debug_trace)
    auth_token = auth["auth_token"]

    payload = build_create_wishlist_payload(
        promoter_name=promoter_name,
        pan=pan,
        gstin=gstin,
        group_name=group_name,
    )

    parsed = _graphql_request(
        payload,
        operation="createWishlistv2",
        auth_token=auth_token,
        debug_trace=debug_trace,
    )
    wishlist = (parsed.get("data") or {}).get("createWishlistV2")

    if not wishlist:
        logger.error(
            "createWishlistV2 returned no data. Full response:\n%s",
            _json_pretty(parsed),
        )
        raise _fail(
            f"RiskMaster API returned no wishlist data: {_json_pretty(parsed)}",
            debug_trace=debug_trace,
        )

    logger.info(
        "=== RiskMaster WISHLIST FLOW SUCCESS === id=%s name=%s",
        wishlist.get("id"),
        wishlist.get("name"),
    )

    return {
        "success": True,
        "requested_at": datetime.now(UTC).isoformat(),
        "auth_method": auth.get("auth_method"),
        "group_name": payload["variables"]["name"],
        "promoter_name": promoter_name,
        "pan": normalize_pan(pan, gstin),
        "gstin": normalize_gstin(gstin) or None,
        "wishlist": wishlist,
        "raw_response": _redact_response(parsed),
        "debug_trace": debug_trace,
        "wishlist_request": _redact_payload(payload),
    }
