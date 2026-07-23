# Job Hunter repository instructions

Before starting work, read:

1. `.ai/PRODUCT_VISION.md`
2. `.ai/PROJECT_RULES.md`
3. `.ai/ARCHITECTURE.md`
4. `.ai/CODING_STANDARDS.md`
5. `.ai/CHECKLIST.md`
6. `.ai/TODO.md`

Instructions in these documents are mandatory unless the user explicitly
requests a justified change to the repository architecture or standards.

## Model and reasoning policy

The repository default is GPT-5.6 Terra with medium reasoning.

Use the normal parent agent for:

- Small, well-defined implementations
- Ordinary API endpoints
- Pydantic models and schemas
- Straightforward provider adapters
- Templates and frontend styling
- Unit tests
- Documentation updates
- Simple bug fixes
- Linting and formatting corrections

Use Plan mode or delegate to the `deep_worker` agent for:

- Architecture decisions
- Complex debugging where the cause is unknown
- Major refactoring
- Repository-wide changes
- Security-sensitive changes
- Database schema and migration changes
- Async or concurrency problems
- Scraper blocking, proxy, retry, timeout, or rate-limit problems
- Job deduplication and normalisation design
- Docker, CI/CD, deployment, and Raspberry Pi resource problems
- Changes spanning three or more architectural layers

Before delegating, provide the agent with:

1. The requested outcome
2. Relevant constraints
3. Known symptoms or failures
4. Required validation commands
5. Files or components already suspected

Do not use high reasoning merely for routine code generation.