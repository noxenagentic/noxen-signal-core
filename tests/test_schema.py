from dataclasses import replace
from datetime import datetime, timedelta, timezone
import unittest

from noxen_signal_core import (
    SIGNAL_SCHEMA_VERSION,
    Signal,
    SignalRisk,
    SignalSide,
    signal_from_dict,
    signal_json_schema,
    signal_to_dict,
    validate_signal,
)


class SignalSchemaTest(unittest.TestCase):
    def _buy_signal(self) -> Signal:
        published_at = datetime.now(timezone.utc)
        return Signal(
            signal_id="btc-1",
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

    def test_validate_buy_signal(self) -> None:
        signal = self._buy_signal()
        validate_signal(signal)
        serialized = signal_to_dict(signal)
        self.assertEqual(serialized["schema_version"], SIGNAL_SCHEMA_VERSION)
        self.assertEqual(serialized["market"], "BTC-USD")
        self.assertEqual(serialized["side"], "buy")
        self.assertEqual(serialized["published_at"][-1], "Z")

    def test_reject_invalid_confidence(self) -> None:
        signal = replace(self._buy_signal(), confidence_bps=6_000)

        with self.assertRaisesRegex(ValueError, "confidence_bps"):
            validate_signal(signal)

    def test_reject_naive_datetimes(self) -> None:
        published_at = datetime.now()
        signal = Signal(
            signal_id="btc-2",
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-2",
        )

        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            validate_signal(signal)

    def test_validate_hold_signal_requires_zero_price_bounds(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc-3",
            market="BTC-USD",
            side=SignalSide.HOLD,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=0.0, entry_max=0.0, stop_loss=0.0, take_profit=0.0),
            metadata_digest="ipfs://signal-3",
        )

        validate_signal(signal)

    def test_reject_sell_signal_with_invalid_bounds(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="eth-1",
            market="ETH-USD",
            side=SignalSide.SELL,
            confidence_bps=8_100,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=2000.0, entry_max=2050.0, stop_loss=2001.0, take_profit=2100.0),
            metadata_digest="ipfs://signal-4",
        )

        with self.assertRaisesRegex(ValueError, "sell risk bounds"):
            validate_signal(signal)

    def test_round_trip_signal_serialization(self) -> None:
        signal = self._buy_signal()
        round_tripped = signal_from_dict(signal_to_dict(signal))

        self.assertEqual(round_tripped, signal)

    def test_reject_unknown_side_from_dict(self) -> None:
        payload = signal_to_dict(self._buy_signal())
        payload["side"] = "long"

        with self.assertRaisesRegex(ValueError, "payload.side"):
            signal_from_dict(payload)

    def test_reject_unsupported_schema_version(self) -> None:
        payload = signal_to_dict(self._buy_signal())
        payload["schema_version"] = "2.0"

        with self.assertRaisesRegex(ValueError, "schema_version"):
            signal_from_dict(payload)

    def test_reject_non_integer_confidence(self) -> None:
        payload = signal_to_dict(self._buy_signal())
        payload["confidence_bps"] = 7500.5

        with self.assertRaisesRegex(ValueError, "confidence_bps must be an integer"):
            signal_from_dict(payload)

    def test_reject_unknown_top_level_field(self) -> None:
        payload = signal_to_dict(self._buy_signal())
        payload["unexpected"] = True

        with self.assertRaisesRegex(ValueError, "unknown fields"):
            signal_from_dict(payload)

    def test_reject_missing_risk_field(self) -> None:
        payload = signal_to_dict(self._buy_signal())
        del payload["risk"]["stop_loss"]

        with self.assertRaisesRegex(ValueError, "missing required fields"):
            signal_from_dict(payload)

    def test_schema_export_matches_current_version(self) -> None:
        schema = signal_json_schema()

        self.assertEqual(schema["properties"]["schema_version"]["const"], SIGNAL_SCHEMA_VERSION)
        self.assertIn("risk", schema["required"])

    def test_reject_invalid_signal_id_with_special_chars(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc/1@invalid#",
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

        with self.assertRaisesRegex(ValueError, "signal_id must contain only"):
            validate_signal(signal)

    def test_reject_oversized_signal_id(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="x" * 129,
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

        with self.assertRaisesRegex(ValueError, "signal_id must be at most 128 characters"):
            validate_signal(signal)

    def test_reject_invalid_market_format(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc-1",
            market="BTCUSD",  # Missing hyphen
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

        with self.assertRaisesRegex(ValueError, "market must match format"):
            validate_signal(signal)

    def test_accept_lowercase_market(self) -> None:
        """Market validation should accept both upper and lower case."""
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc-1",
            market="btc-usd",  # lowercase input
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

        # This should pass - market validation accepts both cases
        validate_signal(signal)

    def test_reject_excessive_signal_lifetime(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc-1",
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(days=31),  # Exceeds 30 day limit
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="ipfs://signal-1",
        )

        with self.assertRaisesRegex(ValueError, "signal lifetime must not exceed 30 days"):
            validate_signal(signal)

    def test_reject_empty_metadata_digest(self) -> None:
        published_at = datetime.now(timezone.utc)
        signal = Signal(
            signal_id="btc-1",
            market="BTC-USD",
            side=SignalSide.BUY,
            confidence_bps=7_500,
            published_at=published_at,
            expires_at=published_at + timedelta(hours=1),
            risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
            metadata_digest="   ",  # Whitespace only
        )

        with self.assertRaisesRegex(ValueError, "metadata_digest must be non-empty"):
            validate_signal(signal)
