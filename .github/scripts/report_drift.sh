#!/usr/bin/env bash
# Fail if regenerating artifacts changed anything that is committed.
#
# Shared by every job in regenerate-artifacts.yml so the failure message is the
# same shape wherever drift appears, and so the "what to do about it" advice
# lives in one place rather than being copied into each job.
set -euo pipefail

layer="${1:-artifacts}"

if git diff --quiet; then
  echo "No drift: the committed ${layer} artifacts match what the code produces."
  exit 0
fi

echo "::error::Committed ${layer} artifacts do not match what the code produces."
echo
echo "Files that changed when regenerated:"
git diff --stat
echo
echo "A diff here means one of two things, and only a human can tell which:"
echo
echo "  1. The artifacts are STALE. An estimator, a scope or a filter changed"
echo "     and the artifacts were never regenerated. Run the same scripts"
echo "     locally and commit the result."
echo
echo "  2. The change was INTENDED but not yet committed alongside its data."
echo "     Same fix, but check the reports quoting these numbers too --"
echo "     tests/test_reports_are_not_stale.py catches the ones it knows about."
echo
echo "What is NOT a cause: new races. Ingestion runs in post-race-refresh.yml"
echo "and is the only thing here allowed to change which races exist."
echo
git --no-pager diff --unified=0 | head -200
exit 1
