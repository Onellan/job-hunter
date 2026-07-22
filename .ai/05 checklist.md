# Change Checklist

## Before implementation

- [ ] Read `.ai/01 project_rules.md` and the relevant sections of
      `.ai/02 architecture.md`.
- [ ] Confirm the change is within the approved milestone and locate the
      correct layer.
- [ ] Search the repository for an existing contract, service, or helper.
- [ ] Identify input, persistence, provider, privacy, and memory implications.
- [ ] Justify every new dependency; prefer an installed dependency or the
      standard library.

## Before handoff

- [ ] Routes are thin; no provider calls or SQL appear in routes/templates.
- [ ] The change has deterministic tests; providers use fixtures/fakes.
- [ ] New public classes/functions have clear type hints and docstrings.
- [ ] Errors are classified, safely logged, and do not discard partial success.
- [ ] Large queries/exports are paginated or streamed; expensive work is
      bounded and cleaned up.
- [ ] Configuration is validated and secrets/PII are absent from source and logs.
- [ ] Relevant docs, changelog, and `.ai/07 todo.md` are updated.
- [ ] `pytest`, Ruff, Black, isort, mypy, and `git diff --check` pass (or any
      exception is reported explicitly).

## Before approval of the next milestone

- [ ] The current milestone is working end-to-end.
- [ ] Acceptance evidence and known limitations have been reported.
- [ ] The next milestone scope is stated without silently expanding it.
