# Architecture: kyverno-finops-policies

> **Why each file exists and what role it plays in the Skill.**

---

## How this Skill differs from Skills 1 and 2

| Dimension | Skill 1 (generator) | Skill 2 (auditor) | Skill 3 (finops) |
|-----------|--------------------|--------------------|-------------------|
| Input | Natural language | YAML files | **Live cost data (MCP) or NL** |
| Output | Policy + tests | Audit report | **FinOps report + policies** |
| Core script role | Quality gate (end) | The product (center) | **Validator + estimator (mid)** |
| Data source | None (static) | None (static) | **MCP server (live)** |
| Cross-skill | Standalone | Invokes Skill 1 | **Invokes Skill 1 + Skill 2** |

---

## Dual-mode design

The Skill auto-detects MCP availability and adapts:

- **Mode A (Standalone):** No MCP. User describes the cost scenario.
  The Skill generates policies from best practices and templates.

- **Mode B (Connected):** MCP available (e.g., OpenCost). The Skill queries
  real allocation data, identifies waste, and generates targeted policies
  based on actual usage.

The expertise is in the Skill. MCP is the data pipe.

---

## File-by-file breakdown

### SKILL.md — The workflow

5-step workflow: Detect Mode → Analyze → Generate → Compose → Report.

Key difference from Skills 1 and 2: Step 1 checks for MCP availability
and adapts the entire workflow accordingly. This is the first Skill
that changes behavior based on external context.

### scripts/finops_analyze.py — Parameter validator + cost estimator

Unlike `validate_policy.py` (quality gate) and `audit_policy.py` (the product),
`finops_analyze.py` runs mid-workflow. It validates FinOps-specific parameters:
tier consistency, label completeness, threshold reasonableness, FOCUS compliance,
and rough cost savings estimates.

Three scripts, three patterns:
- Skill 1: script runs last (validates output)
- Skill 2: script runs first (produces findings for Claude to interpret)
- Skill 3: script runs in the middle (validates parameters before composition)

### references/finops-patterns.md — 5 governance patterns

Tiered limits, cost labels, over-provisioning guards, FOCUS mapping, budget controls.
Each pattern maps to a template in assets/.

### references/focus-mapping.md — FOCUS specification

Maps FOCUS dimensions to Kubernetes labels. Ensures cost reports are consistent
across clusters and cloud providers.

### references/common-waste-patterns.md — Waste scenarios

The 5 most common sources of Kubernetes cost waste, ranked by financial impact.
Claude uses this to contextualize MCP findings.

### assets/templates/ — Policy templates

- `tiered-limits-base.yaml` — environment-aware resource limits
- `cost-labels-base.yaml` — cost-allocation label enforcement
- `overprovision-guard-base.yaml` — over-provisioning block with justification

### assets/templates/finops-report-template.md — Report template

Template for the FinOps governance report output. Claude fills this
with data from the analysis (Mode A or Mode B).

---

## The complete governance loop

```
OpenCost MCP → FinOps Skill → Policy Auditor → Policy Generator
   (data)       (analyze)       (validate)       (test)
```

Three Skills. One MCP server. From live data to tested policy.
