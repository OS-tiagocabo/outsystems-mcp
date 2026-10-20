#!/usr/bin/env bash
# The platform check for customers who connect both the OutSystems 11 (O11)
# and the ODC MCP servers. Pins:
# - the platform check near the top of each of the five lockstepped skill
#   docs, which applies only when both servers are connected: once per doc,
#   ahead of the first section, byte-identical across them;
# - the "Platform first" Rules bullet: once in each doc and byte-identical
#   across them, and the feedback Scope sentence that leaves out the O11 server;
# - the main skill description (claude, cursor, kiro), identical in the three,
#   and the O11 exclusion at the end of each Beta skill description (the
#   Cursor and Kiro copies of the Beta skills are covered by
#   tests/skills/test_harness_copies.py);
# - the README troubleshooting row for a request that lands on the wrong
#   platform, with its link to the docs page.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

MAIN_DESCRIBED=(
  claude/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
  kiro/outsystems/skills/outsystems/SKILL.md
)

BETA_DESCRIBED=(
  claude/skills/outsystems-app-architecture/SKILL.md
  claude/skills/outsystems-custom-code/SKILL.md
  claude/skills/outsystems-dependency-impact/SKILL.md
  claude/skills/outsystems-design-to-app/SKILL.md
  claude/skills/outsystems-spec-driven-build/SKILL.md
  claude/skills/outsystems-tenant-architecture/SKILL.md
)

first_rule_hash=""
first_gate_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  rule=$(grep -F -- '- **Platform first.**' "$REPO_ROOT/$doc")
  check "has the Platform first rule once" "$(printf '%s\n' "$rule" | grep -c .)" 1
  check_match "names the O11 server by role, not only by name" "$rule" 'the Service Studio MCP server \(named `servicestudio` in the O11 setup\)'
  check_match "points to the platform check when both servers are connected" "$rule" 'When both servers are connected, run the platform check at the top of this skill before your first call\.'
  check_match "stops when the O11 server is missing" "$rule" 'start the MCP server in Service Studio and stop'
  check_match "an ODC request that only mentions O11 is for ODC" "$rule" 'A request for work on ODC that only mentions O11, for example recreating an O11 entity in an ODC app, is for ODC\.'
  check_match "keeps the platform for later requests" "$rule" 'treat later requests in this conversation as for that platform unless the user says otherwise\.$'
  gate=$(grep -F -- '**Platform check, only when both OutSystems MCP servers are connected.**' "$REPO_ROOT/$doc")
  check "has the platform check once" "$(printf '%s\n' "$gate" | grep -c .)" 1
  gate_line=$(grep -nF -- '**Platform check, only when both OutSystems MCP servers are connected.**' "$REPO_ROOT/$doc" | cut -d: -f1)
  first_section=$(grep -n '^## ' "$REPO_ROOT/$doc" | head -1 | cut -d: -f1)
  check "platform check comes before the first section" "$([ -n "$gate_line" ] && [ "$gate_line" -lt "$first_section" ] && echo yes || echo no)" yes
  check_match "platform check applies only when both servers are connected" "$gate" 'When tools from the Service Studio MCP server \(O11, named `servicestudio` in the O11 setup\) are also visible in this session'
  check_match "platform check covers read-only calls" "$gate" 'read-only calls such as listing apps included'
  check_match "platform check asks when the request names neither" "$gate" 'if it names neither, as in "my app", ask "Is this for ODC, or for the O11 module open in Service Studio\?" and wait for the answer before calling any tool\.'
  check_match "platform check is skipped with one server" "$gate" 'When only this server is connected, skip this check and go ahead as usual\.$'
  gate_hash=$(printf '%s' "$gate" | git hash-object --stdin)
  [ -n "$first_gate_hash" ] || first_gate_hash=$gate_hash
  check "platform check is byte-identical to ${DOCS[0]}" "$gate_hash" "$first_gate_hash"
  scope=$(grep -F -- '**Scope.**' "$REPO_ROOT/$doc")
  check "has one feedback Scope line" "$(printf '%s\n' "$scope" | grep -c .)" 1
  check_match "feedback Scope leaves out the O11 server" "$scope" 'Tools from the Service Studio MCP server \(named `servicestudio` in the O11 setup\) belong to OutSystems 11 \(O11\): never report on them\.'
  rule_hash=$(printf '%s' "$rule" | git hash-object --stdin)
  if [ -z "$rule_hash" ]; then
    echo "git hash-object returned nothing for $doc" >&2
    exit 1
  fi
  [ -n "$first_rule_hash" ] || first_rule_hash=$rule_hash
  check "Platform first rule is byte-identical to ${DOCS[0]}" "$rule_hash" "$first_rule_hash"
done

section "skill descriptions"
main_description='description: "OutSystems Developer Cloud (ODC) over MCP. Edit apps, publish, deploy, search tenant elements, manage external libraries. Use for ANY OutSystems task on ODC. Not for OutSystems 11 (O11) modules open in Service Studio. When the Service Studio (O11) MCP server is also connected, confirm the platform before the first call."'
for doc in "${MAIN_DESCRIBED[@]}"; do
  check "$doc names ODC and rules out O11" "$(grep -m1 '^description: ' "$REPO_ROOT/$doc")" "$main_description"
done
for doc in "${BETA_DESCRIBED[@]}"; do
  check_match "$doc ends by ruling out O11" "$(grep -m1 '^description: ' "$REPO_ROOT/$doc")" "Not for OutSystems 11 \(O11\) or Service Studio\.[\"']$"
done

README="$REPO_ROOT/README.md"
section "README troubleshooting row"
row=$(grep -F -- '| The agent works on ODC when you meant OutSystems 11 (O11)' "$README")
check "has the troubleshooting row once" "$(printf '%s\n' "$row" | grep -c .)" 1
check_match "troubleshooting row links the docs page" "$row" 'use_outsystems_mcp_in_odc_alongside_o11/\)'

finish
