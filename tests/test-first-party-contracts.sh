#!/bin/sh
set -eu
ROOT=$(CDPATH= cd "$(dirname "$0")/.." && pwd)
AOS=$ROOT/skills/agent-operating-system
TRIAGE=$ROOT/skills/experience-triage/SKILL.md
CASES=$ROOT/skills/experience-triage/references/evaluation-cases.md

grep -q '^schema_version=2$' "$AOS/assets/agent-standards.conf.template"
grep -q '^generator_version=' "$AOS/assets/agent-standards.conf.template"
grep -q 'invoke `experience-triage`' "$AOS/SKILL.md"
grep -q 'does not contain a second experience-classification decision tree' "$AOS/SKILL.md"
grep -q 'Versioning And Upgrades' "$AOS/references/versioning-and-upgrades.md"

for term in observe candidate adopted automated retired; do grep -q "$term" "$TRIAGE"; done
grep -q 'Classify two independent axes' "$TRIAGE"
grep -q 'duplicate, conflict' "$TRIAGE"
grep -q 'hooks require deterministic pass/fail logic' "$TRIAGE"
! grep -qi 'first matching layer' "$TRIAGE"
case_count=$(grep -c '^| ' "$CASES")
[ "$case_count" -ge 20 ]
printf 'First-party skill contract tests passed.\n'
