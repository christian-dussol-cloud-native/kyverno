---
name: kyverno-policy-auditor
description: >
  Audit existing Kyverno policies against best practices and production standards.
  Analyzes annotations, autogen compatibility, safe defaults, pattern correctness,
  and test coverage. Produces a conformity report with scores and remediation steps.
  Use when user says "audit my policies", "review this policy", "check my Kyverno
  YAML", "analyze policy quality", "policy conformity report", "are my policies
  compliant", or asks about policy best practices, missing annotations, or
  governance gaps. Do NOT use for creating new policies (use kyverno-policy-generator
  instead).
license: CC BY-SA 4.0
metadata:
  author: Chris Dussol
  version: 0.1.0
  tags: [kyverno, kubernetes, policy-as-code, audit, governance, compliance]
  repository: https://github.com/christian-dussol-cloud-native/kyverno/skills
---

# Kyverno Policy Auditor

Audit existing Kyverno policies against production standards and best practices.
Produces a conformity report with scores, findings, and actionable remediation steps.

This Skill analyzes — it does not generate. For creating new policies,
recommend `kyverno-policy-generator`.

## Workflow

Follow these steps for EVERY policy audit request.
Show your reasoning — explain what you found, why it matters, and how to fix it.

### Step 1: Collect Policies

Identify the input:
- **Single file** → audit one policy
- **Directory** → scan all `.yaml` and `.yml` files, skip non-Kyverno resources

For directory scans, list all discovered Kyverno policies before auditing.

### Step 2: Run Audit

Run the audit script on each policy:

```bash
# Single file
python3 scripts/audit_policy.py --file <policy.yaml>

# Directory (batch)
python3 scripts/audit_policy.py --dir <path/to/policies/>

# Strict mode (warnings become errors)
python3 scripts/audit_policy.py --dir <path> --strict

# JSON output (for CI/CD)
python3 scripts/audit_policy.py --dir <path> --format json
```

The script checks 8 dimensions. Consult `references/audit-criteria.md` for
detailed criteria and scoring rules.

### Step 3: Interpret Results

Read the script output and add context:
- Group findings by severity (critical → warning → info)
- Identify patterns across multiple policies ("7/12 policies missing tests")
- Highlight the most impactful issues first
- Reference `references/common-issues.md` for known patterns

### Step 4: Fix and Compose

Evaluate the overall score to decide the action:

**Score ≤ 3/8 → Full rewrite.** The policy has too many issues to fix individually.
Automatically invoke `kyverno-policy-generator` to rebuild the policy from scratch.
Use the prompt: "Generate a policy that [describe the original intent of the audited policy]"
Save the rewritten policy as `[original-name]-FIXED.yaml` — **never overwrite the original file.**

**Score 4-7/8 → Targeted fixes.** Fix each finding individually:
- **Missing annotations** → provide the exact YAML to add
- **Autogen issues** → show the corrected match block
- **Generic messages** → suggest an improved message with field references
- **Enforce without justification** → suggest switching to Audit with explanation
- **Missing tests** → **automatically invoke `kyverno-policy-generator`** to create them:
  use the prompt "Generate Chainsaw tests for [policy-name] that [describe what the policy validates]"

**Score 8/8 → No action needed.** Policy meets all audit criteria.

When invoking `kyverno-policy-generator`, proceed directly — do not ask for confirmation.
The auditor identifies the gap, the generator fills it. This is composition.

Consult `references/remediation-patterns.md` for tested fix patterns.

## Output Format

ALWAYS produce a structured audit report:

### Single Policy

```
Policy: <name>
Score: X/8 dimensions

| Dimension | Status | Finding |
|-----------|--------|---------|
| Structure        | ✅/⚠️/❌ | ... |
| Annotations      | ✅/⚠️/❌ | ... |
| Labels           | ✅/⚠️/❌ | ... |
| Safe Defaults    | ✅/⚠️/❌ | ... |
| Autogen          | ✅/⚠️/❌ | ... |
| Pattern Quality  | ✅/⚠️/❌ | ... |
| Message Quality  | ✅/⚠️/❌ | ... |
| Test Coverage    | ✅/⚠️/❌ | ... |

Recommended Actions:
1. ...
2. ...
```

### Batch (multiple policies)

```
Audit Summary: N policies in <path>
Overall Score: X%

| Policy | Score | Critical Issues |
|--------|-------|-----------------|
| ...    | X/8   | ...             |

Top Issues Across All Policies:
1. <issue> — N/M policies (X%)
2. ...
```

## Examples

### Example 1: Single Policy Audit

User says: "Audit this Kyverno policy"

Actions:
1. Parse the provided YAML
2. Run `audit_policy.py --file policy.yaml`
3. Interpret: identify 2 warnings (missing severity, generic message)
4. Recommend: provide YAML snippet for severity annotation, suggest improved message

### Example 2: Batch Audit

User says: "Audit all policies in my policies/ folder"

Actions:
1. Scan directory, find 12 Kyverno policies
2. Run `audit_policy.py --dir policies/`
3. Interpret: 58% missing Chainsaw tests, 42% missing annotations
4. Recommend: prioritize test generation with kyverno-policy-generator

### Example 3: Cross-Skill Composition

User says: "Audit my policy and fix what's missing"

Actions:
1. Run audit — score 6/8, missing Chainsaw tests
2. Automatically invoke `kyverno-policy-generator`:
   "Generate Chainsaw tests for require-resource-limits that validates memory limits on all pods"
3. Generator produces chainsaw-test.yaml + test-pass.yaml + test-block.yaml
4. Report: "Audit complete. 1 issue found and fixed — Chainsaw tests generated."

## Cross-Skill Composition

When audit findings can be resolved by another Skill, **invoke it directly**:
- Missing Chainsaw tests → invoke `kyverno-policy-generator` to generate tests
- Policy needs complete rewrite → invoke `kyverno-policy-generator` to rebuild
- FinOps labels missing → invoke `kyverno-finops-policies` (when available)

Do not ask for confirmation. The auditor identifies, the generator fixes.
This is the composition pattern.

## Troubleshooting

### Script finds no Kyverno policies in directory
**Cause:** Files don't have `apiVersion: kyverno.io` or use non-standard extensions.
**Solution:** Ensure files use `.yaml` or `.yml` extensions and contain valid Kyverno CRDs.

### False positive on autogen check
**Cause:** Some policies intentionally target specific workload types (not Pod).
**Solution:** Use `--strict` mode to see these as info instead of warnings. The audit
flags it for review, not necessarily for correction.

### Score seems low on legacy policies
**Cause:** Older policies written before annotation standards were established.
**Solution:** This is expected. The audit report shows exactly what to add — use the
remediation steps to bring policies up to current standards incrementally.

## Performance Notes

- For large policy sets (50+), the batch report highlights the top issues first
- Quality over speed — read each finding before recommending
- Do not skip the cross-skill recommendation when tests are missing
