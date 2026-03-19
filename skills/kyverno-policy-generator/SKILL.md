---
name: kyverno-policy-generator
description: >
  Generate production-ready Kyverno policies from natural language. Creates validate,
  mutate, generate, and verifyImages policies with Chainsaw tests and kubectl-ready
  output. Use when user says "create Kyverno policy", "enforce resource limits",
  "block privileged containers", "restrict image registries", "require labels",
  "policy-as-code", "admission controller", "Kubernetes governance", or mentions
  Kyverno, ClusterPolicy, compliance, or cluster security. Do NOT use for general
  Kubernetes troubleshooting or non-policy YAML generation.
license: Apache-2.0
metadata:
  author: Chris Dussol
  version: 0.1.0
  tags: [kyverno, kubernetes, policy-as-code, governance, finops, cncf]
  repository: https://github.com/christian-dussol-cloud-native/kyverno/skills
---

# Kyverno Policy Generator

Generate production-ready Kyverno policies from natural language, backed by the
official Kyverno policy library (https://github.com/kyverno/policies — 200+ tested policies).

Every generated policy includes: kubectl-ready YAML, Chainsaw test, and test resources.

## Workflow

Follow these steps for EVERY policy generation request.
Show your reasoning at each step — explain which policy type you detected,
whether you found a match in the official library, and what decisions you made.

### Step 1: Parse Intent

Extract from the user's description:

- **Policy type** — Detect from keywords:
  - validate → "enforce", "require", "block", "deny", "restrict", "must have"
  - mutate → "add", "inject", "default", "auto-add", "automatically set"
  - generate → "create", "auto-create", "provision", "when namespace is created"
  - verifyImages → "image signature", "cosign", "SLSA", "supply chain", "signed"
- **Target resources** — kinds, namespaces, label selectors
- **Rule logic** — what to enforce, modify, or create
- **Action** — Audit (default) or Enforce (only if user explicitly asks)

### Step 2: Match Against Official Library

Check `references/lib-policy-index.md` for existing policies. Decision tree:

1. **Exact match** → Use as base, customize per user requirements
2. **Similar pattern** → Adapt with user-specific parameters
3. **No match** → Generate from scratch using `assets/templates/`

Always mention when a policy is based on an official library policy.

### Step 3: Generate Policy YAML

Consult `references/annotation-standards.md` for required annotations and labels.

Critical rules:
- **ALWAYS** set `validationFailureAction: Audit` by default (safe-first)
- **ALWAYS** include standard Kyverno annotations (title, category, severity, description)
- **ALWAYS** add `app.kubernetes.io/managed-by: kyverno-skills` label
- For Pod-targeting policies, use autogen-compatible structure (target Pod directly)
- Use `"?*"` for "must exist and be non-empty", `"X | Y"` for allowed values

For detailed policy type structures (validate, mutate, generate, verifyImages),
consult `references/policy-patterns.md`.

### Step 4: Generate Chainsaw Test

For EVERY policy, create a Chainsaw test. Use the template from
`assets/templates/chainsaw-test-base.yaml`.

Each test includes:
- Apply the policy, then immediately patch it to `validationFailureAction: Enforce`
  (the policy defaults to Audit for production safety — Enforce is required here so
  the admission webhook actually blocks non-compliant resources during testing)
- Submit a compliant resource (should pass)
- Submit a non-compliant resource (should be blocked)

### Step 5: Validate

```bash
python3 scripts/validate_policy.py --file <generated-policy.yaml>
```

## Output Format

ALWAYS output THREE deliverables:

1. **Policy YAML** — `<policy-name>.yaml` (kubectl-ready)
2. **Chainsaw Test** — `chainsaw-test.yaml`
3. **Test Resources** — `test-pass.yaml` + `test-block.yaml`

## Examples

### Example 1: Resource Limits

User says: "Enforce resource limits on all pods in namespace finance"

Actions:
1. Detect type: validate (keyword "enforce")
2. Match: lib policy `require-requests-limits` (Best Practices category)
3. Customize: add namespace selector for `finance`
4. Generate Chainsaw test with pod that has limits (pass) and without (block)

Result: 3 files — policy targeting finance namespace, Chainsaw test, test resources.

### Example 2: Block Latest Tag

User says: "Block containers using the latest image tag"

Actions:
1. Detect type: validate (keyword "block")
2. Match: lib policy `disallow-latest-tag`
3. Generate with pattern `image: "!*:latest"`
4. Test: pod with `nginx:1.27` (pass) and `nginx:latest` (block)

### Example 3: Auto-Create NetworkPolicy

User says: "Automatically create a default-deny NetworkPolicy when a new namespace is created"

Actions:
1. Detect type: generate (keyword "automatically create", "namespace is created")
2. No exact match — generate from `assets/templates/generate-base.yaml`
3. Configure: match Namespace creation, generate NetworkPolicy with `podSelector: {}`
4. Test: create namespace, assert NetworkPolicy exists

## Common Pattern Quick Reference

| Use Case | Type | Key Pattern |
|----------|------|-------------|
| Require resource limits | validate | `pattern.spec.containers[].resources` |
| Require labels | validate | `pattern.metadata.labels.<key>: "?*"` |
| Restrict registries | validate | `deny` + conditions on image field |
| Block privileged | validate | `securityContext.privileged: "false"` |
| Add default labels | mutate | `patchStrategicMerge.metadata.labels` |
| Create NetworkPolicy | generate | Match Namespace → generate NetworkPolicy |
| Verify cosign | verifyImages | `attestors.entries.keys.publicKeys` |

For 30+ detailed patterns, consult `references/policy-patterns.md`.

## Cross-Skill Recommendations

Suggest complementary skills when relevant:
- Cost/FinOps → `kyverno-finops-policies`
- Compliance frameworks → `kyverno-compliance-auditor`
- OPA/Gatekeeper migration → `kyverno-migration-assistant`
- Testing/CI/CD → `kyverno-policy-validator`

## Troubleshooting

### Policy doesn't block resources
**Cause:** `validationFailureAction` is set to `Audit` (default).
**Solution:** Change to `Enforce` when ready. Always test in Audit mode first.

### Autogen not working for Deployments
**Cause:** Policy targets Deployment directly instead of Pod.
**Solution:** Target Pod in `match.any.resources.kinds`. Kyverno auto-generates
rules for Deployment, StatefulSet, DaemonSet, Job, CronJob.

### "pattern not valid" error
**Cause:** Pattern structure doesn't match the target resource schema.
**Solution:** Check the Kubernetes API spec for the resource kind. Use
`references/policy-patterns.md` for tested patterns.

### "variable present outside of foreach" error
**Cause:** `{{ element.* }}` used in `validate.message`, which is outside the foreach scope.
**Solution:** `element` is only available inside `foreach` blocks (in `key`, `value`, `deny` fields).
The `message` field at the `validate` level must be a **static string** — do not reference `element.*` there.
```yaml
# WRONG
validate:
  message: "Image '{{ element.image }}' is invalid."  # element not available here
  foreach: [...]

# CORRECT
validate:
  message: "An image is invalid. Check all containers."  # static message
  foreach: [...]
```

### "entered value of `operator` is invalid" error
**Cause:** An unsupported operator was used in `deny.conditions` (e.g. `Contains`, `NotContains`).
**Solution:** Kyverno does not have `Contains`/`NotContains`. For string containment checks, use
`Equals`/`NotEquals` with wildcard patterns instead:
- "image contains `:latest`" → `operator: Equals, value: "*:latest"`
- "image has no `:`" → `operator: NotEquals, value: "*:*"`

Full list of valid operators: `Equals`, `NotEquals`, `Equal`, `NotEqual`, `In`, `NotIn`,
`AnyIn`, `AnyNotIn`, `AllIn`, `AllNotIn`, `GreaterThan`, `GreaterThanOrEquals`, `LessThan`,
`LessThanOrEquals`, `DurationGreaterThan`, `DurationGreaterThanOrEquals`, `DurationLessThan`,
`DurationLessThanOrEquals`.

### Chainsaw test fails with "error expected but resource was admitted"
**Cause:** Policy is in Audit mode (doesn't block, only reports).
**Solution:** Set `validationFailureAction: Enforce` in the policy for testing,
or adjust the Chainsaw test to check PolicyReport instead.

## Performance Notes

- Take time to generate well-structured, commented YAML
- Quality over speed — validate before presenting to user
- Do not skip the Chainsaw test generation step
