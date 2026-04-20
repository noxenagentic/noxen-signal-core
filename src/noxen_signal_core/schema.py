from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any


SIGNAL_SCHEMA_VERSION = "1.0"
MIN_CONFIDENCE_BPS = 7_000
MAX_CONFIDENCE_BPS = 10_000
SIGNAL_PAYLOAD_FIELDS = frozenset(
    {
        "schema_version",
        "signal_id",
        "market",
        "side",
        "confidence_bps",
        "published_at",
        "expires_at",
        "risk",
        "metadata_digest",
    }
)
SIGNAL_RISK_FIELDS = frozenset({"entry_min", "entry_max", "stop_loss", "take_profit"})

# Validation constraints
MAX_SIGNAL_ID_LENGTH = 128
MAX_MARKET_LENGTH = 32
MAX_METADATA_DIGEST_LENGTH = 256
SIGNAL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MARKET_PATTERN = re.compile(r"^[A-Z]{2,6}-[A-Z]{2,6}$")  # e.g., BTC-USD, ETH-USDT
MAX_SIGNAL_LIFETIME = timedelta(days=30)


class SignalSide(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass(slots=True, frozen=True)
class SignalRisk:
    entry_min: float
    entry_max: float
    stop_loss: float
    take_profit: float


@dataclass(slots=True, frozen=True)
class Signal:
    signal_id: str
    market: str
    side: SignalSide
    confidence_bps: int
    published_at: datetime
    expires_at: datetime
    risk: SignalRisk
    metadata_digest: str


def _require_non_empty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _require_signal_id(value: object) -> str:
    """Validate signal_id format and length."""
    if not isinstance(value, str):
        raise ValueError("signal_id must be a string")
    stripped = value.strip()
    if len(stripped) > MAX_SIGNAL_ID_LENGTH:
        raise ValueError(f"signal_id must be at most {MAX_SIGNAL_ID_LENGTH} characters")
    if not SIGNAL_ID_PATTERN.match(stripped):
        raise ValueError("signal_id must contain only alphanumeric characters, hyphens, and underscores")
    return stripped


def _require_market(value: object) -> str:
    """Validate market identifier format (e.g., BTC-USD)."""
    if not isinstance(value, str):
        raise ValueError("market must be a string")
    stripped = value.strip()
    if len(stripped) > MAX_MARKET_LENGTH:
        raise ValueError(f"market must be at most {MAX_MARKET_LENGTH} characters")
    # Accept both upper and lower case, but validate against uppercase pattern
    if not MARKET_PATTERN.match(stripped.upper()):
        raise ValueError("market must match format like BTC-USD or ETH-USDT (with hyphen)")
    return stripped


def _require_metadata_digest(value: object) -> str:
    """Validate metadata digest format and length."""
    if not isinstance(value, str):
        raise ValueError("metadata_digest must be a string")
    stripped = value.strip()
    if len(stripped) > MAX_METADATA_DIGEST_LENGTH:
        raise ValueError(f"metadata_digest must be at most {MAX_METADATA_DIGEST_LENGTH} characters")
    if not stripped:
        raise ValueError("metadata_digest must be non-empty")
    return stripped


def _require_timezone_aware_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValueError(f"{field} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be timezone-aware")
    return value


def _require_signal_side(value: object) -> SignalSide:
    if not isinstance(value, SignalSide):
        raise ValueError("side must be a SignalSide value")
    return value


def _require_supported_schema_version(value: object) -> str:
    if not isinstance(value, str) or value != SIGNAL_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {SIGNAL_SCHEMA_VERSION}")
    return value


def _require_exact_fields(payload: dict[str, Any], expected: frozenset[str], field: str) -> None:
    actual = set(payload)
    unknown = sorted(actual - expected)
    missing = sorted(expected - actual)

    if missing:
        raise ValueError(f"{field} is missing required fields: {', '.join(missing)}")
    if unknown:
        raise ValueError(f"{field} has unknown fields: {', '.join(unknown)}")


def _serialize_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_signal(signal: Signal) -> None:
    if not isinstance(signal, Signal):
        raise ValueError("signal must be a Signal instance")

    # Use strict validators for critical fields
    _require_signal_id(signal.signal_id)
    _require_market(signal.market)
    _require_signal_side(signal.side)

    if not isinstance(signal.confidence_bps, int) or isinstance(signal.confidence_bps, bool):
        raise ValueError("confidence_bps must be an integer")
    if not MIN_CONFIDENCE_BPS <= signal.confidence_bps <= MAX_CONFIDENCE_BPS:
        raise ValueError(f"confidence_bps must be between {MIN_CONFIDENCE_BPS} and {MAX_CONFIDENCE_BPS}")

    published_at = _require_timezone_aware_datetime(signal.published_at, "published_at")
    expires_at = _require_timezone_aware_datetime(signal.expires_at, "expires_at")

    if expires_at <= published_at:
        raise ValueError("expires_at must be after published_at")

    # Validate signal lifetime is reasonable
    signal_lifetime = expires_at - published_at
    if signal_lifetime > MAX_SIGNAL_LIFETIME:
        raise ValueError(f"signal lifetime must not exceed {MAX_SIGNAL_LIFETIME.days} days")

    _require_metadata_digest(signal.metadata_digest)

    risk = signal.risk
    if not isinstance(risk, SignalRisk):
        raise ValueError("risk must be a SignalRisk instance")

    for field_name, value in (
        ("entry_min", risk.entry_min),
        ("entry_max", risk.entry_max),
        ("stop_loss", risk.stop_loss),
        ("take_profit", risk.take_profit),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"risk.{field_name} must be a number")

    if signal.side is SignalSide.HOLD:
        if any(value != 0 for value in (risk.entry_min, risk.entry_max, risk.stop_loss, risk.take_profit)):
            raise ValueError("hold signals must not carry price bounds")
        return

    if min(risk.entry_min, risk.entry_max, risk.stop_loss, risk.take_profit) <= 0:
        raise ValueError("priced signals must use positive price bounds")
    if risk.entry_min > risk.entry_max:
        raise ValueError("entry_min must be less than or equal to entry_max")

    if signal.side is SignalSide.BUY:
        if risk.stop_loss >= risk.entry_min or risk.take_profit <= risk.entry_max:
            raise ValueError("buy risk bounds are inconsistent")
        return

    if risk.stop_loss <= risk.entry_max or risk.take_profit >= risk.entry_min:
        raise ValueError("sell risk bounds are inconsistent")


def signal_to_dict(signal: Signal) -> dict[str, Any]:
    validate_signal(signal)
    return {
        "schema_version": SIGNAL_SCHEMA_VERSION,
        "signal_id": signal.signal_id,
        "market": signal.market,
        "side": signal.side.value,
        "confidence_bps": signal.confidence_bps,
        "published_at": _serialize_datetime(signal.published_at),
        "expires_at": _serialize_datetime(signal.expires_at),
        "risk": {
            "entry_min": float(signal.risk.entry_min),
            "entry_max": float(signal.risk.entry_max),
            "stop_loss": float(signal.risk.stop_loss),
            "take_profit": float(signal.risk.take_profit),
        },
        "metadata_digest": signal.metadata_digest,
    }


def signal_from_dict(payload: dict[str, Any]) -> Signal:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dictionary")

    _require_exact_fields(payload, SIGNAL_PAYLOAD_FIELDS, "payload")
    _require_supported_schema_version(payload["schema_version"])

    risk_payload = payload.get("risk")
    if not isinstance(risk_payload, dict):
        raise ValueError("payload.risk must be a dictionary")
    _require_exact_fields(risk_payload, SIGNAL_RISK_FIELDS, "payload.risk")

    try:
        side = SignalSide(payload["side"])
    except KeyError as exc:
        raise ValueError("payload.side is required") from exc
    except ValueError as exc:
        raise ValueError("payload.side must be one of: buy, sell, hold") from exc

    try:
        published_at = datetime.fromisoformat(str(payload["published_at"]).replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(str(payload["expires_at"]).replace("Z", "+00:00"))
    except KeyError as exc:
        raise ValueError("payload published_at and expires_at are required") from exc
    except ValueError as exc:
        raise ValueError("published_at and expires_at must be ISO-8601 datetimes") from exc

    signal = Signal(
        signal_id=payload["signal_id"],
        market=payload["market"],
        side=side,
        confidence_bps=payload["confidence_bps"],
        published_at=published_at,
        expires_at=expires_at,
        risk=SignalRisk(
            entry_min=risk_payload["entry_min"],
            entry_max=risk_payload["entry_max"],
            stop_loss=risk_payload["stop_loss"],
            take_profit=risk_payload["take_profit"],
        ),
        metadata_digest=payload["metadata_digest"],
    )
    validate_signal(signal)
    return signal


def signal_json_schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://schemas.noxen.ai/signal.json",
        "title": "NOXEN Signal",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema_version",
            "signal_id",
            "market",
            "side",
            "confidence_bps",
            "published_at",
            "expires_at",
            "risk",
            "metadata_digest",
        ],
        "properties": {
            "schema_version": {"type": "string", "const": SIGNAL_SCHEMA_VERSION},
            "signal_id": {"type": "string", "minLength": 1},
            "market": {"type": "string", "minLength": 1},
            "side": {"type": "string", "enum": [side.value for side in SignalSide]},
            "confidence_bps": {
                "type": "integer",
                "minimum": MIN_CONFIDENCE_BPS,
                "maximum": MAX_CONFIDENCE_BPS,
            },
            "published_at": {"type": "string", "format": "date-time"},
            "expires_at": {"type": "string", "format": "date-time"},
            "risk": {
                "type": "object",
                "additionalProperties": False,
                "required": ["entry_min", "entry_max", "stop_loss", "take_profit"],
                "properties": {
                    "entry_min": {"type": "number"},
                    "entry_max": {"type": "number"},
                    "stop_loss": {"type": "number"},
                    "take_profit": {"type": "number"},
                },
            },
            "metadata_digest": {"type": "string", "minLength": 1},
        },
    }
