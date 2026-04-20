# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial signal schema with `Signal`, `SignalRisk`, `SignalSide` dataclasses
- Signal validation with timezone-aware datetime checks
- JSON serialization/deserialization with schema versioning
- JSON Schema export for downstream consumers
- Comprehensive test suite (12 tests)

### Security
- Minimum confidence threshold: 7000 bps (70%)
- HOLD signals enforce zero price bounds
- BUY/SELL signals enforce directional risk consistency
