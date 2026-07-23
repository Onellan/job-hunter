# Provider management

Open **Providers** to register, enable, disable, edit, or remove a provider
without calling the JSON API. A saved search can run only against enabled
providers that match its optional provider-code criteria.

Provider configuration entered through the browser is deliberately limited to
non-secret JSON objects of at most 10,000 characters. Credential-like keys are
rejected in both browser and API validation. Store credentials in deployment
configuration or another secret-management boundary, never in Job-Hunter's
provider records.

Removal requires a checkbox confirmation. Existing provider-run history is a
durable reference and may prevent removal; disable the provider instead when
you need to preserve that history.
