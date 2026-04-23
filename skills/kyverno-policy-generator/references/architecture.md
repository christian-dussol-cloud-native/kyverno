# Architecture: kyverno-policy-generator

> **Why each file exists and what role it plays in the Skill.**

This document explains the design decisions behind the `kyverno-policy-generator` Skill.
If you're a contributor, a curious engineer, or building your own Claude Code Skill,
this is where the "how it works under the hood" lives.

---

## How a Claude Code Skill works

A Skill is a folder that teaches Claude how to handle specific tasks.
It uses a three-level progressive disclosure system:

| Level | What loads | When |
|-------|-----------|------|
| **Frontmatter** (YAML header in SKILL.md) | Always — part of Claude's system prompt | Every conversation |
| **SKILL.md body** (instructions) | When Claude thinks the Skill is relevant | On trigger match |
| **Bundled files** (scripts, references, assets) | When Claude needs them during execution | On demand |

This means Claude doesn't load everything at once. The frontmatter is the trigger,
the body is the workflow, and the bundled files are the depth. This keeps the
context window efficient while maintaining specialized expertise.

---

## File-by-file breakdown

### SKILL.md — The brain

```
kyverno-policy-generator/
└── SKILL.md
```

**What it is:** The only required file. Contains YAML frontmatter (trigger conditions)
and Markdown instructions (the 6-step workflow).

**Why it's designed this way:**

The **frontmatter** has two jobs: tell Claude *when* to activate (trigger phrases like
"create Kyverno policy", "enforce resource limits") and *when not to* ("Do NOT use for
general Kubernetes troubleshooting"). The `description` field is what Claude reads to
decide if this Skill is relevant — it's the most important 540 characters in the project.

The **body** contains the 6-step workflow that Claude follows for every policy generation.
It's deliberately concise (~160 lines) because everything Claude reads consumes context
window tokens. Detailed patterns, templates, and library indexes are delegated to
`references/` and `assets/` — loaded only when needed.

---

### scripts/validate_policy.py — The quality gate

```
kyverno-policy-generator/
└── scripts/
    └── validate_policy.py
```

**What it does:** Validates generated policies through 4 sequential passes.

**The 4 passes:**

1. **YAML syntax** — Can the file be parsed? Catches malformed YAML before anything else.
2. **Required Kyverno fields** — Does it have `apiVersion: kyverno.io/v1`, `kind: ClusterPolicy`,
   and `spec.rules`? Catches hallucinated field names (a common LLM failure mode).
3. **Annotations** — Are the standard Kyverno annotations present (`title`, `category`,
   `severity`, `description`)? Without these, the policy is invisible to PolicyReports,
   Kyverno Monitor, and Grafana dashboards.
4. **Rules validation** — Is the match structure autogen-compatible (targets Pod, not
   Deployment)? Are messages actionable? Is `validationFailureAction` set?

**Why it's a script, not just instructions:**

The Anthropic Skills guide says it best: "Code is deterministic; language interpretation
isn't." Telling Claude "make sure annotations are present" is a suggestion. Running
`validate_policy.py --file policy.yaml` and getting `FAIL: missing annotation
policies.kyverno.io/severity` is a fact.

**Usage:** `python3 scripts/validate_policy.py --file <policy.yaml> [--strict] [--json]`

- `--strict` treats warnings as errors (useful in CI/CD)
- `--json` outputs machine-readable results
- Exit code 0 (pass) or 1 (fail) for pipeline integration

---

### references/policy-patterns.md — The pattern library

```
kyverno-policy-generator/
└── references/
    └── policy-patterns.md
```

**What it is:** 30+ Kyverno policy patterns organized by category.

**Categories covered:** Resource Management, Pod Security, Image Security, Labels &
Annotations, Networking, Namespace Governance, RBAC & Multi-Tenancy, Probes &
Reliability, Storage, and FinOps-Specific patterns.

**Why it exists:**

When Claude generates a policy, it needs to know the correct Kyverno syntax for each
use case. A generic LLM might use `"*"` where Kyverno requires `"?*"`, or target
Deployment where it should target Pod. This file contains tested patterns — not
training data approximations, but syntax verified against actual Kyverno behavior.

The FinOps-Specific section contains custom patterns not found in the official library:
`require-finops-labels`, `enforce-max-cpu-per-pod`, `enforce-spot-for-non-prod`,
`restrict-pv-size`. These come from real production use cases in financial services
environments.

---

### references/lib-policy-index.md — The official library index

```
kyverno-policy-generator/
└── references/
    └── lib-policy-index.md
```

**What it is:** An index of 200+ policies from the official Kyverno policy library
(https://github.com/kyverno/policies), organized by category.

**Categories indexed:** PSA Baseline/Restricted, Best Practices, CIS Kubernetes
Benchmark, NIST SP 800-53, Networking, Resource Management, Image Security &
Supply Chain, Multi-Tenancy.

**Why it exists:**

Step 2 of the workflow is "Match Against Official Library." Before generating anything
from scratch, Claude checks this index. If an official policy exists for the user's
request, Claude uses it as a base and customizes. This ensures policies are built on
tested foundations, not hallucinated from training data.

This is one of the key differentiators versus a generic LLM: the Skill knows what
already exists in the ecosystem and reuses it.

---

### references/annotation-standards.md — The metadata conventions

```
kyverno-policy-generator/
└── references/
    └── annotation-standards.md
```

**What it is:** The standard Kyverno annotation and label conventions that every
generated policy must follow.

**What it defines:**

- Required annotations: `policies.kyverno.io/title`, `category`, `severity`,
  `subject`, `minversion`, `description`
- Required labels: `app.kubernetes.io/managed-by: kyverno-skills`,
  `kyverno-skills/type: <validate|mutate|generate|verifyImages>`
- Severity levels and when to use each (low, medium, high, critical)
- Category taxonomy

**Why it exists:**

Without annotations, a Kyverno policy is invisible to governance tooling. PolicyReports
can't categorize it. Kyverno Monitor can't display it. Grafana dashboards can't filter
it. In a regulated environment, an unannotated policy is an audit finding.

This file ensures Claude always generates policies that are first-class citizens
in the Kyverno ecosystem — not orphan YAML files.

---

### assets/templates/ — The base templates

```
kyverno-policy-generator/
└── assets/
    └── templates/
        ├── validate-base.yaml
        ├── mutate-base.yaml
        ├── generate-base.yaml
        ├── verify-images-base.yaml
        └── chainsaw-test-base.yaml
```

**What they are:** Fully commented YAML templates for each Kyverno policy type
and for Chainsaw tests.

**Why 5 templates:**

Each Kyverno rule type has different structure, defaults, and gotchas:

- **validate-base.yaml** — `pattern` vs `deny` alternatives, `validationFailureAction: Audit`
  default, `background: true` for scanning existing resources
- **mutate-base.yaml** — `patchStrategicMerge` with `+()` conditional prefix,
  `background: false` (mutations only apply at admission time)
- **generate-base.yaml** — Namespace-triggered resource generation with
  `synchronize: true` to keep generated resources in sync
- **verify-images-base.yaml** — Cosign keys + keyless (Sigstore/Fulcio) + SLSA
  attestation options. `validationFailureAction: Enforce` (image verification is
  typically enforced, not audited)
- **chainsaw-test-base.yaml** — 3-step test structure: apply policy → compliant
  resource passes → non-compliant resource blocked

**Why templates matter:**

When Step 3 ("Generate Policy YAML") finds no match in the official library, Claude
falls back to these templates. They encode the correct defaults, structure, and
comments for each policy type. Without them, Claude would generate from memory —
which means from training data, which means from blog posts of varying quality.

---

## Design principles

**Audit-first:** Every validate policy defaults to `Audit`, not `Enforce`. This
is a deliberate safety choice. Applying an `Enforce` policy to a live cluster
blocks all non-compliant resources immediately — one `kubectl apply` can cause
an outage. `Audit` lets you see what would be blocked without breaking anything.

**Autogen-compatible:** Validate and mutate policies target `Pod`, not `Deployment`.
Kyverno's autogen feature automatically generates matching rules for Deployment,
StatefulSet, DaemonSet, Job, and CronJob. Targeting Deployment directly bypasses
autogen, leaving other workload types unprotected.

**Test everything:** Every policy comes with a Chainsaw test. No exceptions. The test
includes a compliant resource (should pass) and a non-compliant resource (should be
blocked). This is the minimum viable test — you know the policy works before it
reaches any cluster.

**Reuse before create:** The Skill checks the official Kyverno policy library
(200+ policies) before generating anything from scratch. If a tested policy exists,
it uses it as a base. This prevents hallucinated patterns and builds on community-
verified foundations.

**Progressive disclosure:** The SKILL.md body is ~160 lines. Detailed patterns,
library indexes, and annotation standards live in `references/`. Templates live
in `assets/`. Claude loads them on demand, not upfront. This keeps the context
window lean.
