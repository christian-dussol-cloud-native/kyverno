---
name: kyverno-finops-policies
description: >
  Generate Kyverno policies for FinOps cost governance on Kubernetes,
  based on real cost data from OpenCost. Queries OpenCost MCP server
  to identify over-provisioned namespaces, missing cost-allocation
  labels, and budget drift. Generates targeted policies: tiered resource
  limits, cost-allocation labels, over-provisioning guards. Use when
  user says "finops", "cost governance", "analyze cluster costs",
  "optimize cluster costs", "resource limits by environment",
  "cost allocation labels", "prevent over-provisioning", or mentions
  cost-center, chargeback, or cloud cost optimization.
  Requires OpenCost MCP server connected. Do NOT use for general
  Kyverno policy generation (use kyverno-policy-generator) or policy
  auditing (use kyverno-policy-auditor).
license: CC BY-SA 4.0
metadata:
  author: Christian Dussol
  version: 0.1.0
  tags: [kyverno, kubernetes, finops, cost-governance, policy-as-code, mcp, opencost]
  repository: https://github.com/christian-dussol-cloud-native/kyverno/skills
---

# Kyverno FinOps Governance

Generate Kyverno policies for FinOps cost governance on Kubernetes,
based on real cost data from OpenCost.

This Skill closes the FinOps governance loop: it queries OpenCost
(CNCF Sandbox project) for actual cluster usage, identifies waste,
and generates targeted policies to prevent it. Then it invokes the
auditor and generator to validate and test the generated policies.

**Prerequisite:** OpenCost MCP server must be connected to Claude Code.
See repository README for setup instructions.

## Workflow

Follow these steps for EVERY FinOps governance request.

### Step 1: Query OpenCost for Cost Data

Call the OpenCost MCP tools to get current cluster cost data:
- `get_allocation` — cost allocation by namespace/pod/container
- `get_assets` — asset costs (nodes, disks, load balancers)
- `get_cloud_costs` — cloud cost data with provider/service/region filtering

Focus on:
- Top 5-10 namespaces by spend
- Pods with significant gap between requested and actual usage (>50% waste)
- Resources without cost-allocation labels
- Namespaces without resource limits

### Step 2: Analyze and Identify Governance Drift

For each finding, classify the issue:
- **Over-provisioning** → namespace requests far more than it uses
- **Missing labels** → no team, cost-center, or environment label
- **No limits** → pods running without resource limits
- **Tier inconsistency** → dev pods larger than prod pods

Summarize findings in a brief report before generating policies.
Reference `references/common-waste-patterns.md` for context on
typical waste sources.

### Step 3: Generate FinOps Policies

Select the appropriate pattern from `references/finops-patterns.md`
based on findings:
- **Over-provisioning detected** → use `assets/templates/tiered-limits-base.yaml`
- **Missing labels** → use `assets/templates/cost-labels-base.yaml`
- **Need justification workflow** → use `assets/templates/overprovision-guard-base.yaml`

Generate policy YAML with:
- Environment-aware rules (different limits for dev/staging/prod)
- FOCUS™ compliant cost-allocation annotations (see `references/focus-mapping.md`)
- Audit mode by default (safe-first, consistent with Skill 1)
- Full annotations (title, category: FinOps, severity, description)

Run validation:
```bash
python3 scripts/finops_analyze.py --file <policy.yaml>
```

The script validates:
1. Tier consistency (dev limits < staging < prod)
2. Label completeness (all required cost-allocation labels present)
3. Threshold reasonableness (not too low, not too high)
4. Annotation format (FOCUS™ compliance)
5. Cost impact estimate (rough monthly savings)

### Step 4: Compose with Other Skills

**This step is mandatory. Execute immediately after Step 3 — no pause, no recap, no user confirmation.**

After generating FinOps policies, invoke the other Skills automatically in this order:

- **First, invoke `kyverno-policy-generator`** to create Chainsaw tests
  for each generated FinOps policy. This builds the complete deliverable
  (policy + tests) before validation.

- **Then, invoke `kyverno-policy-auditor`** to validate the complete deliverable
  against the 8 audit dimensions (structure, annotations, labels, safe defaults,
  autogen, pattern quality, message quality, test coverage). With tests included,
  expected score is 8/8.

Steps 3 → 4 → 5 run as a single uninterrupted flow. Only produce the final report (Step 5) once the auditor has run. A recap or summary before the auditor runs is a workflow error.

### Step 5: Produce Report

Generate a FinOps governance report using `assets/templates/finops-report-template.md`:

- Current cost state (from OpenCost data)
- Top findings (over-provisioned namespaces, missing labels)
- Policies generated (with filenames)
- Audit scores (from kyverno-policy-auditor)
- Expected savings estimate
- Compliance percentage (what % of namespaces would pass)
- Recommended rollout plan (Audit → monitor → Enforce)

## Output Format

ALWAYS produce:
1. FinOps governance report (with findings and savings estimate)
2. Policy YAML file(s)
3. Chainsaw tests (via kyverno-policy-generator)

## Examples

### Example 1: Full Cost Analysis

User says: "Analyze my cluster costs and suggest governance policies"

Actions:
1. Query OpenCost MCP: top 5 over-provisioned namespaces, resources without labels
2. Findings: "dev-team-a requests 8 cores, uses 1.2 (85% waste). 30% of pods missing cost-center label."
3. Generate: tiered-limits policy (dev: 2 cores max) + cost-labels policy
4. Run `finops_analyze.py` → estimated savings: ~$340/month
5. Invoke generator → Chainsaw tests for both policies
6. Invoke auditor → both policies score 8/8 (with tests)
7. Report: 2 policies, current state, findings, savings estimate, rollout plan

### Example 2: Targeted Tiered Limits

User says: "Generate FinOps policies for the prod-payments namespace"

Actions:
1. Query OpenCost MCP for prod-payments allocation data
2. Findings: namespace properly sized, but no over-provisioning guard
3. Generate `overprovision-guard-base.yaml` with justification requirement
4. Run `finops_analyze.py` → threshold reasonable
5. Invoke generator + auditor
6. Report: 1 policy, justification workflow documented

### Example 3: Label Compliance Audit

User says: "Which namespaces are missing cost-allocation labels?"

Actions:
1. Query OpenCost MCP for unallocated costs (resources without labels)
2. List namespaces missing required labels (team, cost-center, environment)
3. Generate `cost-labels-base.yaml` to enforce labels
4. Invoke generator + auditor
5. Report: list of non-compliant namespaces, policy generated, expected compliance impact

## MCP Tools (OpenCost — Required)

The Skill expects these OpenCost MCP tools to be available:
- `get_allocation(window, aggregate)` — cost allocation by namespace/pod/container
- `get_assets(window)` — asset costs (nodes, disks, load balancers)
- `get_cloud_costs(window)` — cloud cost data

If MCP tools are not available, inform the user that OpenCost must be
connected first. Do not generate policies without real data — that's the
purpose of this Skill.

## Cross-Skill Composition

This Skill invokes both other Skills automatically in sequence:

1. After generating a FinOps policy → invoke `kyverno-policy-generator` to create Chainsaw tests
2. Then invoke `kyverno-policy-auditor` to validate the complete deliverable (policy + tests)
3. If audit score ≤ 3/8 → invoke `kyverno-policy-generator` to rebuild (save as -FIXED.yaml)

Three Skills. One MCP server. From live data to tested policy.

## Troubleshooting

### MCP server not detected
**Cause:** OpenCost not installed or port-forward not active.
**Solution:** Ensure `kubectl port-forward svc/opencost 8081:8081` is running.
Verify with `claude mcp list`. See repository README for full setup.

### Empty or unrealistic cost data
**Cause:** OpenCost needs ~15-20 minutes to collect allocation data after install.
**Solution:** Wait for data collection. Deploy sample workloads first for meaningful data.

### Tiered limits seem wrong
**Cause:** Default tiers may not match the user's environment naming convention.
**Solution:** Specify environment labels explicitly: "my environments use labels env=development, env=staging, env=production"

## Performance Notes

- Limit MCP queries to top 5-10 findings to keep reports actionable
- Generate one policy per FinOps pattern (don't bundle tiered limits + labels in one policy)
- Always start with Audit mode — FinOps policies need monitoring before enforcement
