## Summary

## Security and privacy impact

## Tests run

- [ ] `python -m pytest -q`
- [ ] `python -m ruff check .`
- [ ] `python -m ruff format --check .`
- [ ] `python -m mypy src/cleandrop`

## Checklist

- [ ] Uses only synthetic fixtures.
- [ ] Does not add network uploads, telemetry, accounts, LLMs, or external APIs.
- [ ] Does not log raw OCR, PII, or full input paths.
- [ ] Preserves original files and mandatory verification.
