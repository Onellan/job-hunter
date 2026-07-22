# Job-Hunter Product Vision

## The product

Job-Hunter is a lightweight, self-hosted workspace that gathers relevant job
listings from approved sources into one reliable, searchable view. Its purpose
is to replace repetitive portal visits without making the user surrender their
data to a heavyweight hosted platform.

## Primary outcome

A job seeker should be able to define a search once, run it manually or on a
schedule, review only new or changed matching roles, and act on them from one
fast interface. The platform succeeds when it replaces visiting several job
boards each morning.

## Users

- Professionals actively looking for roles
- Career coaches helping a small number of clients
- Recruiters and power users who need an organised, self-hosted research tool

The first experience is single-user and local-first. Multi-user collaboration,
OAuth, and recruiter CRM capabilities are future work, not assumptions that
complicate the core product today.

## Core experience

1. Define a precise search: keywords/Boolean terms, exclusions, company and
   location filters, remote preference, salary, experience, age, and sources.
2. Run enabled providers safely and see per-provider progress and failures.
3. Store one normalised, deduplicated result set with stable job details.
4. Filter, sort, bookmark, annotate, mark applied, and export the useful jobs.
5. Schedule repeat searches and review what is new since the last run.
6. Use transparent, deterministic scoring before opting into any external AI.

## Product principles

- **Private by default:** self-hosted data and no secret or personal-data logs.
- **Useful under failure:** one broken source does not hide successful results.
- **Explainable:** scores, deduplication, filters, and errors have clear reasons.
- **Fast enough to use daily:** server-rendered pages, focused HTMX updates,
  indexed SQLite queries, and no blocking scrape requests.
- **Small by design:** the base process remains suitable for 1 GB hardware;
  browser automation and optional integrations are bounded and opt-in.
- **Extensible without rewrites:** a new provider or output format is an
  adapter, not a cross-application refactor.

## Provider strategy

The initial provider path is JobSpy, followed by direct portal adapters where a
source needs it (starting with Pnet). Future adapters may support Careers24,
CareerJunction, OfferZen, Greenhouse, Workday, Lever, SmartRecruiters, Ashby,
and other applicant-tracking systems. Availability depends on source terms,
technical stability, and responsible rate limits.

## Non-goals for the initial product

- A social network, recruiter CRM, or general-purpose ATS
- Browser automation running on every page load
- Distributed workers, queues, or cloud-only infrastructure
- A single opaque AI score that cannot be explained
- Heavy SPA behaviour or a client-side data store

## Success measures

- A configured search completes with isolated provider failures and durable run
  history.
- Common dashboard and paginated-results views respond in under one second on
  representative local data.
- The idle base service stays below 100 MB RAM when measured on target-class
  hardware.
- A user can identify new, relevant jobs and apply from the source in minutes,
  without manually collating multiple portals.
