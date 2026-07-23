#!/bin/sh
set -eu

# Provider dependencies and Chromium are baked into the image. Startup must
# never contact a portal or download a browser.
python -m alembic upgrade head
exec job-hunter
