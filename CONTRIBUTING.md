# Contributing

## Workflow

1. Open an issue or write a short proposal for schema changes before changing the public payload shape.
2. Add or update tests for every validation or serialization change.
3. Keep backward compatibility unless you are intentionally introducing a new schema version.
4. Run the test suite before opening a pull request.

## Standards

- Treat the serialized signal payload as a public contract.
- Do not make silent breaking changes to field names, value types, or datetime format.
- Prefer explicit runtime validation over implicit coercion.
