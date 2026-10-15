#!/usr/bin/env bash
# Contract of the Caveats bullet for a deployment that does not serve the
# app model graph yet. On such a deployment the server leaves
# `context_graph` out of `tools/list` and refuses a call by name with
# `data.code = "tool_unavailable_on_transport"`. The bullet names both
# signals, forbids a retry there, and routes the agent to the app's
# references and the per-type context lookups. It also says what
# `refs_fallback_unavailable` means there. It is byte-identical in the
# five lockstepped skill docs. The Branch B of the dependency-impact skill
# carries the same refusal rule, so an agent never reports it as no
# dependencies.

. "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

DOCS=(
  SKILL.md
  claude/skills/outsystems/SKILL.md
  copilot/skill.md
  kiro/outsystems/skills/outsystems/SKILL.md
  cursor/skills/outsystems/SKILL.md
)

caveat_bullet() { # doc -> the withheld-graph Caveats bullet
  grep -F -- '- **Not every deployment serves the app model graph.**' "$REPO_ROOT/$1"
}

section_body() { # doc, heading line -> the lines under it, up to the next heading
  awk -v h="$2" '$0 == h { on = 1; next } on && /^#/ { exit } on' "$REPO_ROOT/$1"
}

first_hash=""
for doc in "${DOCS[@]}"; do
  section "$doc"
  caveat=$(caveat_bullet "$doc")
  check "carries the withheld-graph bullet once" "$(printf '%s\n' "$caveat" | grep -c .)" 1
  check "sits the bullet under ### Caveats" \
    "$(section_body "$doc" '### Caveats' | grep -cF -- "$caveat")" 1
  check_match "says the tool is absent from tools/list" \
    "$caveat" '`context_graph` is absent from `tools/list`'
  check_match "names the refusal code of a call by name" \
    "$caveat" 'returns `data.code = "tool_unavailable_on_transport"`'
  check_match "forbids a retry on that deployment" \
    "$caveat" 'Do not retry the call on that deployment\.'
  check_match "routes dependencies to the app's references" \
    "$caveat" "the app's references for its dependencies"
  check_match "routes elements to the per-type context lookups" \
    "$caveat" 'the per-type context lookups for its elements'
  check_match "says refs_fallback_unavailable lists no dependencies yet" \
    "$caveat" "answer \`refs_fallback_unavailable\`, this deployment cannot list that app's dependencies yet\\."
  check_match "forbids a retry on a not_indexed refusal" \
    "$caveat" 'With `fallbackReason` `not_indexed`, do not retry the call\.'
  check_match "says empty lookups do not prove an empty app" \
    "$caveat" 'Empty per-type lookups then do not prove that the app has no elements, so tell the user that\.'

  hash=$(printf '%s' "$caveat" | git hash-object --stdin)
  [ -n "$first_hash" ] || first_hash=$hash
  check "bullet is byte-identical to ${DOCS[0]}" "$hash" "$first_hash"
done

IMPACT_DOCS=(
  claude/skills/outsystems-dependency-impact/SKILL.md
  cursor/skills/outsystems-dependency-impact/SKILL.md
  kiro/outsystems/skills/outsystems-dependency-impact/SKILL.md
)

branch_b() { # doc -> the Branch B block, heading through the next branch
  awk '/^\*\*Branch B/ { on = 1 } /^\*\*Branch C/ { exit } on' "$REPO_ROOT/$1"
}

for doc in "${IMPACT_DOCS[@]}"; do
  section "$doc"
  block=$(branch_b "$doc" | tr '\n' ' ')
  check_match "names refs_fallback_unavailable in Branch B" "$block" '`refs_fallback_unavailable`'
  check_match "never reports the refusal as no dependencies" \
    "$block" 'never report it as "no dependencies"'
  check_match "forbids a retry on a not_indexed refusal" \
    "$block" 'With `fallbackReason` `not_indexed`, do not retry\.'
done

finish
