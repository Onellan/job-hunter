# Explainable scoring

Job-Hunter's first scoring engine is deterministic and runs entirely in the
application process. It sends no job description, profile preference, or other
data to an external service. The “AI score” shown in the workspace is therefore
an explainable match score, not an opaque model output.

## Configure a profile

Set the local profile in `config/config.yaml` or through `JOB_HUNTER_SCORING__`
environment variables:

```yaml
scoring:
  target_roles: [data engineer]
  skills: [python, sql, azure]
  minimum_salary: 90000
  remote_preference: remote
  minimum_experience_years: 5
  leadership: true
  project_management: true
  business_analysis: false
  agile: true
```

Only configured dimensions are included in the 0–100 score. An empty profile
returns a zero score with a clear configuration reason instead of pretending to
know the user's priorities.

## Dimensions and explanations

The engine compares role phrases, skills, disclosed salary, work arrangement,
experience language, leadership, project-management, business-analysis, and
Agile terms. Skill points are proportional to matched skills. Every result
contains the score, data confidence, matched skills, missing skills, and a
short reason for each enabled dimension.

Confidence measures whether the job provided data for the configured criteria;
it is not a probability that the role is suitable. Undisclosed salary,
experience, or workplace information lowers confidence but does not create a
negative score.

## API and UI

Retrieve a current score without storing a second copy of the job:

```text
GET /api/v1/jobs/{job_id}/score
```

The job detail page renders the same service result. Scores are recalculated on
read, so changing configuration or refreshed job content takes effect without
a migration or background task.

## Future external AI

External AI remains opt-in future work. It must have explicit consent,
configuration, failure handling, and privacy review before it can receive any
job or user data. It will remain separate from this deterministic baseline.
