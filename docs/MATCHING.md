# Resume matching

Job-Hunter supports an opt-in, local-only resume matching workflow. It accepts
explicitly consented plain text through the matching page or the
`PUT /api/v1/resume-profile` API. The current milestone intentionally accepts
text instead of PDF or DOCX files: it avoids parser attack surface and keeps
memory and CPU use predictable on 1 GB devices.

The source resume text is processed in memory and discarded immediately. The
database retains only a bounded, deterministic list of extracted skills, the
consent timestamp and version, and the update timestamp. It never stores the
text, a file name, MIME type, source URL, or file hash. Delete the profile with
`DELETE /api/v1/resume-profile` to permanently remove retained derived skills.

Extraction is local, deterministic, and vocabulary-based; it recognises a
small built-in list plus `resume.skill_vocabulary`. It does not infer skills or
send any information to an external AI service. `POST /api/v1/jobs/compare`
compares two or three existing jobs on demand; comparison results are not
persisted.

In the browser, select two or three jobs in the Jobs workspace and choose
**Compare selected**. The comparison form deliberately never asks users to
copy durable job identifiers. The form remains a normal HTML POST when
JavaScript is unavailable.

Resume-derived skills are sensitive personal data. Enable authentication before
using this feature on a shared or network-accessible deployment, and remember
that SQLite backups include the derived skill profile. Do not commit real
resumes or deployment backups.
