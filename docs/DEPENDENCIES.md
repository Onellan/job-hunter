# Dependency maintenance

## JobSpy compatibility source

Job-Hunter supports Python 3.12, 3.13, and 3.14. PyPI's `python-jobspy` 1.1.82
artifact declares an exact `NUMPY==1.26.3` dependency, which cannot resolve on
every supported Python version. The application therefore installs JobSpy from
the maintained fork [`Onellan/JobSpy`](https://github.com/Onellan/JobSpy) at
commit `7160d0faeda408d246e6948f2cc28ec253883375`. The matching maintenance tag
is `job-hunter-python-jobspy-1.1.82-numpy-compat.1`.

That commit contains upstream's narrowly scoped metadata change from
`NUMPY==1.26.3` to `numpy>=1.26.0`. It retains the `python-jobspy` 1.1.82
package version and public `jobspy.scrape_jobs` API. `pyproject.toml` pins the
commit, rather than relying on the mutable tag, so an installation is
reproducible even if the fork's branches change. The requirement uses GitHub's
HTTPS source archive for that commit, not a `git+` URL; Docker and bare-metal
installs therefore do not require a Git executable.

## Update and upstream-sync policy

1. Check the upstream `speedyapply/JobSpy` release source and dependency
   metadata before changing this pin.
2. Prefer an upstream release that resolves on every currently supported
   Job-Hunter Python version. Remove the fork only after a clean install and
   provider contract tests prove that replacement.
3. If a fork is still necessary, base it on one exact upstream commit and keep
   the fork delta limited to dependency metadata. Do not change JobSpy scraper
   code or its public API as part of compatibility maintenance.
4. Create a new descriptive maintenance tag, record both tag and full commit
   in this document, and update the immutable commit in `pyproject.toml`.
5. Run the package metadata test, a clean `pip install -e ".[dev]"`, provider
   fixture tests, and the normal quality gate before accepting the update.

The fork is a compatibility source, not a provider behaviour fork. Job-Hunter
continues to enforce its own three-site allow-list before calling JobSpy.
