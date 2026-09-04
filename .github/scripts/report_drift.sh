#!/usr/bin/env bash
# Fail if regenerating artifacts left the working tree different from the repo.
#
# Shared by every job in regenerate-artifacts.yml so the failure message is the
# same shape wherever drift appears, and so the "what to do about it" advice
# lives in one place rather than being copied into each job.
#
# This used to ask `git diff --quiet`, which answers "did any TRACKED file
# change?". That is not the question. The question is "does the working tree
# match the repository?", and the difference between the two is exactly a file
# nobody committed.
#
# It cost three weeks of silent drift. run_endurance_audit_cases.py wrote
# reports/imsa/audit_cases.md and reports/imsa/gt3_audit_cases.md; neither path
# was ever committed. Git had reports/imsa/gtp/audit_cases.md and
# reports/imsa/gtd/audit_cases.md instead -- hand-copied once and regenerated
# never. So every run produced untracked files the check could not see, while
# the stale tracked copies it could see never changed, and the job passed green
# with six numbers in a published report drifted from the tables above them.
#
# `git status --porcelain` sees both: modified tracked files AND untracked ones.
set -euo pipefail

layer="${1:-artifacts}"

changed="$(git status --porcelain)"

if [ -z "${changed}" ]; then
  echo "No drift: the committed ${layer} artifacts match what the code produces,"
  echo "and every file the generators wrote is one the repository tracks."
  exit 0
fi

echo "::error::Regenerating the ${layer} artifacts changed the working tree."
echo
echo "What changed:"
echo "${changed}"
echo

if echo "${changed}" | grep -q '^??'; then
  echo "Lines beginning '??' are UNTRACKED -- a generator wrote to a path the"
  echo "repository does not carry. That is worse than ordinary drift, because"
  echo "nothing downstream reads that file: readers, links and the drift check"
  echo "itself all see whatever stale copy IS committed. Either commit the new"
  echo "path and delete the copy it replaces, or point the generator back at"
  echo "the committed path."
  echo
fi

echo "Tracked files that differ:"
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
