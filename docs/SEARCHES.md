# Saved searches

Open **Searches** in the primary navigation to create reusable collection
criteria without using the JSON API. Comma-separated inputs become bounded,
provider-neutral lists; the search form validates all values before it is
stored.

Each detail page supports editing and enablement. **Run now** queues one
provider run per enabled provider that matches the optional provider-code
filter, then refreshes only the run-status panel. It does not wait for scraping
to finish. If no enabled provider matches, the page keeps the failure message
in the panel and makes no external request.

Provider runs show queued, running, succeeded, failed, or cancelled status and
safe error summaries. The list is bounded to the latest 25 records to keep the
page responsive on SQLite and Raspberry Pi deployments.

The same page manages daily or five-field cron schedules. Each schedule retains
only its ten latest dispatch outcomes on the page, including safe failure
summaries and provider-run counts. **Run now** queues a dispatch; it never
waits for provider scraping in the browser request.
