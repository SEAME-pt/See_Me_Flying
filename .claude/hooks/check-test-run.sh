#!/bin/bash
# PreToolUse hook (Bash): before Claude runs `git commit`, check whether code under
# seame-docker/ros2_ws/ goes into the commit without a test run from
# seame-docker/scripts/run_tests.sh going in with it. If so, stop the commit and
# tell Claude to ask the user whether to run the tests first.
#
# Counts as "going in": files already staged, plus, when the same command runs
# `git add` or `git commit -a`, files changed in the working tree (they're about
# to be staged). Skip on purpose by prefixing the command with TESTS_SKIPPED=1.

cmd=$(jq -r '.tool_input.command // empty')
grep -qE '(^|[;&|[:space:]])git( -C [^ ]+)? commit\b' <<<"$cmd" || exit 0
grep -q 'TESTS_SKIPPED=1' <<<"$cmd" && exit 0

repo=${CLAUDE_PROJECT_DIR:-.}
files=$(git -C "$repo" diff --cached --name-only 2>/dev/null)
changes=$(git -C "$repo" status --porcelain --untracked-files=all 2>/dev/null)
if grep -qE '\bgit( -C [^ ]+)? add\b' <<<"$cmd"; then
    files+=$'\n'$(cut -c4- <<<"$changes")                    # may stage anything
elif grep -qE '\bgit( -C [^ ]+)? commit\b.* -[a-zA-Z]*a' <<<"$cmd"; then
    files+=$'\n'$(grep -v '^??' <<<"$changes" | cut -c4-)    # -a: tracked files only
fi

grep -q '^seame-docker/ros2_ws/' <<<"$files" || exit 0
grep -q '^seame-docker/logs/tests/[^/]*/report.md' <<<"$files" && exit 0

jq -n '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny",
  permissionDecisionReason: "Commit not run: code under seame-docker/ros2_ws/ is going into this commit, but no test run (seame-docker/logs/tests/<run>/) is. Ask the user whether to run ./scripts/run_tests.sh first and include the run folder and logs/tests/history.csv in this commit. If they say no, run the same commit again with TESTS_SKIPPED=1 in front of it."}}'
