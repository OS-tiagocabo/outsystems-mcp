#!/usr/bin/env bash
# The "Platform first" Rules bullet: present once in each of the five
# lockstepped skill docs and byte-identical across them. The skill and Beta
# skill descriptions rule out OutSystems 11, and the feedback scope leaves out
# the O11 server. The Cursor and Kiro copies of the Beta skills are covered by
# tests/skills/test_harness_copies.py.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

DESCRIBED=(
  claude/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
  kiro/outsystems/skills/outsystems/SKILL.md
  claude/skills/outsystems-app-architecture/SKILL.md
  claude/skills/outsystems-dependency-impact/SKILL.md
  claude/skills/outsystems-design-to-app/SKILL.md
  claude/skills/outsystems-tenant-architecture/SKILL.md
)

first_rule_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  rule=$(grep -F -- '- **Platform first.**' "$REPO_ROOT/$doc")
  check "has the Platform first rule once" "$(printf '%s\n' "$rule" | grep -c .)" 1
  check_match "asks when the platform is unclear" "$rule" 'Is this for ODC, or for the O11 module open in Service Studio\?'
  check_match "stops when the O11 server is missing" "$rule" 'start the MCP server in Service Studio and stop'
  check_match "feedback leaves out the O11 server" "$(cat "$REPO_ROOT/$doc")" 'Tools from the `servicestudio` server belong to OutSystems 11 \(O11\): never report on them\.'
  rule_hash=$(printf '%s' "$rule" | git hash-object --stdin)
  [ -n "$first_rule_hash" ] || first_rule_hash=$rule_hash
  check "Platform first rule is byte-identical to ${DOCS[0]}" "$rule_hash" "$first_rule_hash"
done

section "skill descriptions"
for doc in "${DESCRIBED[@]}"; do
  check_match "$doc rules out O11" "$(grep -m1 '^description: ' "$REPO_ROOT/$doc")" 'Not for OutSystems 11 \(O11\)'
done

finish
