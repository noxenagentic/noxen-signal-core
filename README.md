# noxen-signal-core

Canonical signal schema library for NOXEN AI systems.

## Installation

```bash
pip install noxen-signal-core
```

## Scope

- Signal enums and dataclasses
- Risk envelope fields
- Confidence and schedule validation
- Transport-safe serialization helpers

## Public API

- `SignalSide`: signal direction enum
- `SignalRisk`: entry and exit envelope
- `Signal`: canonical signal object
- `SIGNAL_SCHEMA_VERSION`: current wire-format version
- `validate_signal(signal)`: runtime validation for external inputs
- `signal_to_dict(signal)`: JSON-safe payload serialization
- `signal_from_dict(payload)`: strict payload parsing back into `Signal`
- `signal_json_schema()`: machine-readable JSON schema for downstream consumers

## Production Notes

- Datetimes must be timezone-aware.
- `signal_to_dict` serializes datetimes as UTC ISO-8601 strings.
- Serialized payloads include `schema_version` and `signal_from_dict` rejects unsupported versions.
- `HOLD` signals must use zeroed price bounds.
- `BUY` and `SELL` signals enforce directional stop-loss and take-profit consistency.

## Quick Start

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests
```

```python
from datetime import datetime, timedelta, timezone

from noxen_signal_core import Signal, SignalRisk, SignalSide, signal_to_dict, validate_signal

published_at = datetime.now(timezone.utc)
signal = Signal(
    signal_id="btc-1",
    market="BTC-USD",
    side=SignalSide.BUY,
    confidence_bps=7500,
    published_at=published_at,
    expires_at=published_at + timedelta(hours=1),
    risk=SignalRisk(entry_min=100.0, entry_max=102.0, stop_loss=95.0, take_profit=110.0),
    metadata_digest="ipfs://signal-1",
)

validate_signal(signal)
payload = signal_to_dict(signal)
```

## Compatibility

- Current schema version: `1.0`
- Any breaking wire-format change should ship under a new schema version instead of silently changing the existing payload shape.

## Test

```bash
env PYTHONPATH=src python3 -m unittest discover -s tests
```

## Development

```bash
# Clone repository
git clone https://github.com/noxenagentic/noxen-signal-core.git
cd noxen-signal-core

# Install in editable mode
pip install -e .

# Run tests
python -m unittest discover -s tests

# Run type checking
mypy src/
```

## Contributing

Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on submitting issues and pull requests.

## License

MIT License — see [LICENSE](LICENSE) for details.
