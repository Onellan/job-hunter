# Job-Hunter Roadmap

## Completed milestones

- [x] Milestone 1 — Foundation
- [x] Milestone 2 — Domain and persistence
- [x] Milestone 3 — Provider platform
- [x] Milestone 4 — Search workspace
- [x] Milestone 5 — Export
- [x] Milestone 6 — Scheduler
- [x] Milestone 7 — Direct Pnet provider
- [x] Milestone 8 — Explainable scoring
- [x] Milestone 9 — Authentication and notifications
- [x] Milestone 10 — Advanced matching

The completed implementation detail for these milestones is retained in the
architecture and feature documentation under `docs/`, the changelog, and the
Git history. The completed UI-review tasks UI-001 through UI-012 are summarised
in `.ai/UI_REVIEW.md`; they are intentionally removed from this active backlog.

## Milestone 11 — Release Quality

- [ ] Run `python scripts/benchmark.py --database data/benchmark.db` on the
      intended Raspberry Pi 4 Model B with 1 GB RAM, using the production-like
      optional features. Record OS image, Python version, enabled extras, idle
      operating-system RSS, startup latency, and dashboard latency in
      `docs/RELEASE.md`.
  - **Acceptance:** idle RSS is below 100 MB, startup is below 3 seconds, and
    dashboard latency is below 1 second on that target device.
- [x] Accessibility, security, backup/restore, Docker, documentation, and
      manual browser release checks. See `docs/RELEASE.md` for the dated local
      baseline and the remaining target-device gate.
- [x] Release notes and reproducible release checklist.
