# Common Issues

The most frequent findings when auditing Kyverno policies, ranked by frequency.

## 1. Missing Chainsaw Tests (60%+ of audited policies)

**Why it matters:** Without tests, you can't verify the policy actually blocks
what it should block and admits what it should admit. In regulated environments,
untested policies are an audit finding.

**Fix:** Use `kyverno-policy-generator` to create tests:
"Generate Chainsaw tests for [policy-name] that [describe what it validates]"

## 2. Missing Annotations (40-50%)

**Why it matters:** Annotations make policies visible to PolicyReports, Kyverno
Monitor, and Grafana dashboards. Without them, the policy exists but can't be
governed, filtered, or reported on.

**Most commonly missing:** `severity` and `subject`.

## 3. Generic Error Messages (30-40%)

**Why it matters:** "Resource limits are required" doesn't tell the developer
which container, which field, or where to find guidance. In a cluster with
50+ deployments, generic messages create support tickets.

**Good pattern:**
```
Container '{{ element.name }}' in Pod '{{ request.object.metadata.name }}'
is missing required resource limits. Add resources.limits.memory to all
containers. See: https://kyverno.io/policies/
```

## 4. Enforce Without Justification (20-30%)

**Why it matters:** `Enforce` blocks all non-compliant resources immediately.
If existing workloads don't comply, they can't be updated, restarted, or scaled.
One `kubectl apply` can cause an outage.

**Fix:** Switch to `Audit` first. Review PolicyReports. Move to `Enforce`
only after confirming no existing workloads will break.

## 5. Targeting Deployment Instead of Pod (15-25%)

**Why it matters:** Kyverno's autogen feature generates matching rules for
Deployment, StatefulSet, DaemonSet, Job, and CronJob when you target Pod.
Targeting Deployment directly means everything else is unprotected.

**Fix:** Change `kinds: [Deployment]` to `kinds: [Pod]` in the match block.

## 6. Using "*" Instead of "?*" (10-20%)

**Why it matters:** In Kyverno pattern matching, `"*"` matches any value
including empty string. `"?*"` means "must exist AND be non-empty."
Using `"*"` means `limits: {}` passes validation.

## 7. Missing background: true (10-15%)

**Why it matters:** Without `background: true`, validate policies only check
resources at admission time. Existing non-compliant resources in the cluster
are never flagged in PolicyReports.

## 8. Invalid Operators (5-10%)

**Why it matters:** Operators like `Contains` or `NotContains` don't exist in
Kyverno. They fail silently or throw cryptic errors.

**Valid operators:** Equals, NotEquals, In, NotIn, AnyIn, AnyNotIn, AllIn,
AllNotIn, GreaterThan, GreaterThanOrEquals, LessThan, LessThanOrEquals,
and their Duration variants.
