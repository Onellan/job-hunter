# Engineering Principles

Use these principles to resolve ordinary design choices without adding process.

1. **Make the smallest correct change.** Prefer a focused adapter, contract, or
   query over a new subsystem.
2. **Measure before optimising.** Profile memory, query plans, and scrape time;
   do not add caches, workers, or async complexity based on intuition.
3. **Keep work durable.** Persist jobs and run state; never make a user depend
   on an in-memory task surviving a restart.
4. **Bound expensive work.** Browser processes, provider concurrency, retries,
   exports, and database transactions must have explicit limits.
5. **Make failure visible and contained.** Preserve partial provider success,
   show useful status, and record safe diagnostics.
6. **Prefer contracts over reach-through.** Depend on a small interface instead
   of importing another layer's implementation.
7. **Prefer server-rendered, accessible HTML.** Use HTMX for focused updates
   and JavaScript only for behaviour HTML/HTMX cannot provide.
8. **Preserve optionality cheaply.** SQLite-first configuration and adapter
   boundaries are enough for future PostgreSQL or new providers; do not build
   the future system in advance.

If an option materially changes scope, privacy, resource use, or user-facing
behaviour and the requirement is unclear, state the trade-off and ask before
implementing it.
