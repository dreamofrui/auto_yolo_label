# Utils Layer

`utils/` is shared infrastructure. It owns durable mapping/task formats,
business error metadata, path encoding, device probing, and loguru setup. It
must not import `core/` or GUI modules; core and GUI may depend on these
contracts.

## Read Before Editing

- [Shared infrastructure](./shared-infrastructure.md)
- `AGENTS.md` architecture constraints
- the focused utility test named in the topic file

## Quality Check

- Use `pathlib.Path` and UTF-8 file I/O.
- Preserve JSON field names and stable `ErrorCode` values unless a product
  migration explicitly changes the contract.
- Keep hardware and optional third-party imports lazy where the module is also
  used by CPU-only tooling or tests.
- Run the focused utility tests plus `tests/test_imports.py` and
  `scripts/check_disciplines.py` for boundary changes.
