# Architecture: kyverno-policy-auditor

> **Why each file exists and what role it plays in the Skill.**

---

## How this Skill differs from kyverno-policy-generator

| Dimension | Generator (Skill 1) | Auditor (Skill 2) |
|-----------|--------------------|--------------------|
| Input | Natural language | Existing YAML files |
| Output | Policy + tests | Audit report + remediation |
| Core script role | Quality gate (end of workflow) | The product (center of workflow) |
| Multi-file | No | Yes (directory scan) |
| Cross-skill | Standalone | Recommends Skill 1 for remediation |

---

## File-by-file breakdown

### SKILL.md — The workflow

The 4-step audit workflow: Collect → Run Audit → Interpret → Recommend.

The key difference from Skill 1: Step 2 runs a script that IS the product,
not a validation step at the end. Claude's value is in Step 3 (interpreting
patterns across multiple policies) and Step 4 (recommending specific fixes
and cross-skill actions).

The negative trigger is important: "Do NOT use for creating new policies
(use kyverno-policy-generator instead)." This teaches Claude to route
generation requests to the right Skill.

### scripts/audit_policy.py — The core engine

Unlike Skill 1's `validate_policy.py` (which validates the Skill's own output),
`audit_policy.py` analyzes arbitrary user-provided YAML. It must handle:
- Malformed YAML
- Non-Kyverno resources (skip gracefully)
- Legacy policies (pre-annotation standards)
- Hand-written policies with inconsistent structure

The script checks 8 dimensions and supports:
- `--file` for single policy audit
- `--dir` for batch directory scan
- `--strict` for CI/CD (warnings become errors)
- `--format json` for machine-readable output

### references/audit-criteria.md — Scoring rules

Detailed pass/warn/fail criteria for each dimension. Claude consults this
when it needs to explain why a specific finding was flagged.

### references/common-issues.md — Frequency-ranked problems

The most frequent audit findings, ranked by how often they appear in
real-world policy sets. Claude uses this to contextualize findings:
"Missing tests is the most common issue — affecting 60%+ of audited policies."

### references/remediation-patterns.md — Fix snippets

Ready-to-use YAML for each common fix. Instead of telling the user
"add annotations," Claude provides the exact YAML to paste.

---

## Design principle: the script IS the product

In Skill 1, the workflow is:
```
NL → Claude generates → YAML → validate_policy.py checks
```

In Skill 2, the workflow is:
```
YAML → audit_policy.py analyzes → Claude interprets results
```

The script runs first, not last. Claude's role shifts from creator to
interpreter. This is a fundamentally different Skill pattern — and it
demonstrates that Skills are not just code generators.
