# Kyverno Skills for Claude Code

> **Kyverno policies from natural language, with tests included.**

Generate, audit and govern Kubernetes policies using Claude Code Skills,
backed by the [official Kyverno policy library](https://github.com/kyverno/policies) (200+ tested policies).

---

## Context

There are three ways teams write Kyverno policies today:

- **Manual:** search docs, copy-paste YAML, hope it works.
- **Ask an AI:** Faster, looks right — until it breaks production. No validation, no governance, no confidence.
- **Ask a colleague:** implicit knowledge. Works until they leave.

All three share the same problem: **no validation, no tests, no confidence.**

My Kyverno Skills fix this by encoding production experience into disciplined, deterministic workflows.

---

## Available Skills

### kyverno-policy-generator

Generate Kyverno policies from natural language descriptions.

**What it does:**
- Parses intent → detects validate / mutate / generate / verifyImages
- Matches against 200+ official Kyverno policies before generating from scratch
- Produces kubectl-ready YAML with full annotations and labels
- Auto-generates Chainsaw tests (pass + block resources) for every policy
- Validates with a 4-pass script (YAML → structure → annotations → rules)
- Defaults to Audit mode. Always.

**What's inside:**

```
kyverno-policy-generator/
├── SKILL.md                           # 6-step workflow
├── scripts/
│   └── validate_policy.py             # 4-pass validation
├── references/
│   ├── policy-patterns.md             # 30+ patterns
│   ├── lib-policy-index.md            # 200+ official policies index
│   └── annotation-standards.md        # Kyverno annotation conventions
└── assets/templates/
    ├── validate-base.yaml
    ├── mutate-base.yaml
    ├── generate-base.yaml
    ├── verify-images-base.yaml
    └── chainsaw-test-base.yaml
```

> Want to understand how each file works under the hood? See [architecture.md](kyverno-policy-generator/references/architecture.md).

---

### kyverno-policy-auditor

Audit existing Kyverno policies against best practices and production standards.

**What it does:**
- Audits single files or entire directories of Kyverno policies
- Checks 8 dimensions: structure, annotations, labels, safe defaults, autogen, pattern quality, message quality, test coverage
- Produces a conformity report with scores and actionable remediation steps
- Automatically invokes `kyverno-policy-generator` when tests are missing (cross-skill composition)
- Supports `--strict` mode for CI/CD and `--format json` for automation

**What's inside:**

```
kyverno-policy-auditor/
├── SKILL.md                           # 4-step audit workflow
├── scripts/
│   └── audit_policy.py                # 8-dimension audit engine
├── references/
│   ├── audit-criteria.md              # Scoring rules per dimension
│   ├── common-issues.md               # Frequency-ranked findings
│   ├── remediation-patterns.md        # YAML fix snippets
│   └── architecture.md                # Design decisions
└── examples/
    ├── good-policy.yaml               # Well-structured (score 6-7/8)
    ├── bad-policy.yaml                # Generic LLM output (score 1/8)
    ├── medium-policy.yaml             # Missing annotations (score 4-5/8)
    └── mutate-policy.yaml             # Mutate policy (score 5-6/8)
```

**Test the auditor with the included examples:**

```bash
# Install the Skill
cp -r kyverno-policy-auditor ~/.claude/skills/

# Launch Claude Code
claude

# Try these prompts:
> "Audit the policy in kyverno-policy-auditor/examples/bad-policy.yaml"
> "Audit all policies in kyverno-policy-auditor/examples/"
> "Review good-policy.yaml and tell me what's missing"
```

**Example — auditing a generic LLM-generated policy:**

```
$ python3 audit_policy.py --file require-resource-limits.yaml

🔍 Kyverno Policy Auditor
==================================================
📄 Policy: require-resource-limits
📊 Score: 1/8

  ✅ Structure
  ❌ Annotations      No annotations defined
  ⚠️ Labels           No labels defined
  ⚠️ Safe Defaults    Enforce mode — ensure intentional
  ⚠️ Autogen          match.resources without any: wrapper
  ⚠️ Pattern Quality  "*" instead of "?*"
  ⚠️ Message Quality  Message too short (15 chars)
  ❌ Test Coverage     No test coverage

❌ 2 critical issue(s) to fix.
```

> The generator creates. The auditor reviews. Together, they form a governance ecosystem.

---

### kyverno-finops-policies

Generate Kyverno policies for FinOps cost governance on Kubernetes,
based on real cost data from OpenCost.

**What it does:**
- Queries OpenCost MCP server for live cluster cost allocation data
- Identifies over-provisioned namespaces, missing cost-allocation labels, and budget drift
- Generates environment-tiered resource limits (dev / staging / prod)
- Enforces cost-allocation labels (team, cost-center, environment, service)
- Guards against over-provisioning with justification annotations
- Validates with `finops_analyze.py`: tier consistency, thresholds, FOCUS™ compliance, cost estimate
- Automatically invokes `kyverno-policy-generator` to create Chainsaw tests
- Then invokes `kyverno-policy-auditor` to validate the complete deliverable

**Prerequisite:** OpenCost MCP server connected to Claude Code (see setup below).

**What's inside:**

```
kyverno-finops-policies/
├── SKILL.md                           # 5-step FinOps governance workflow
├── scripts/
│   └── finops_analyze.py              # Parameter validator + cost estimator
├── references/
│   ├── finops-patterns.md             # 5 governance patterns
│   ├── focus-mapping.md               # FOCUS™ specification mapping
│   ├── common-waste-patterns.md       # Typical waste scenarios
│   └── architecture.md                # Design decisions
└── assets/templates/
    ├── tiered-limits-base.yaml        # Environment-aware resource limits
    ├── cost-labels-base.yaml          # Cost-allocation label enforcement
    ├── overprovision-guard-base.yaml   # Over-provisioning guard with justification
    └── finops-report-template.md      # Report template
```

**Test the FinOps Skill with OpenCost (live cost data):**

For the complete demo, you'll need Minikube + OpenCost. The `finops-demo-scripts/`
folder includes scripts to set up and tear down the demo environment.

```bash
cd finops-demo-scripts/
chmod u+x *.sh

./01-start-minikube.sh         # Start Minikube with adequate resources
./02-install-opencost.sh       # Install Prometheus + OpenCost
./03-deploy-demo-workloads.sh  # Deploy sample pods to generate cost data
./03b-wait-for-data.sh         # Poll OpenCost API — exits when data is ready
./04-connect-mcp.sh            # Port-forward + register MCP with Claude Code
```

In a new terminal, install all 3 Skills and test the full loop:

```bash
cp -r kyverno-policy-generator kyverno-policy-auditor kyverno-finops-policies ~/.claude/skills/

claude
> "Analyze my cluster costs and suggest governance policies"
```

Expected behavior:
1. The FinOps Skill detects the OpenCost MCP and queries cost allocation data
2. It identifies waste in dev-team-a (over-provisioned pod)
3. It generates targeted FinOps policies based on actual usage
4. It automatically invokes `kyverno-policy-generator` to create Chainsaw tests
5. It then invokes `kyverno-policy-auditor` to validate the complete deliverable
6. Final output: policies, tests, and a FinOps governance report

When done:

```bash
./05-cleanup.sh                # Remove resources, optionally stop Minikube
```

See `finops-demo-scripts/README.md` for full details on each script.

### Troubleshooting

**"No cost data" error** → OpenCost hasn't collected enough data yet. Wait 20 minutes.

**MCP server not detected** → Verify `kubectl port-forward` is still running (script 04
keeps it alive in the background). Check `claude mcp list` shows opencost as healthy.

**Wrong Skill triggered** → If the auditor triggers when you wanted FinOps, the
descriptions need refinement. Try: `> "Use kyverno-finops-policies to..."`

**OpenCost pod not ready** → Increase Minikube resources:
`./05-cleanup.sh` then `minikube start --memory 6144 --cpus 4` and re-run scripts 02-04.

> The generator creates. The auditor reviews. The FinOps Skill connects to the real world. Three Skills. One governance ecosystem.

---

## Quick Start

### Claude Code (Terminal)

```bash
# Clone the repo
git clone https://github.com/christian-dussol-cloud-native/kyverno/
cd kyverno/skills

# Install all 3 Skills
mkdir -p ~/.claude/skills/
cp -r kyverno-policy-generator ~/.claude/skills/
cp -r kyverno-policy-auditor ~/.claude/skills/
cp -r kyverno-finops-policies ~/.claude/skills/

# Launch Claude Code in your terminal
claude

# The Skills trigger automatically on relevant prompts
> "Block any container using the latest image tag in production"
> "Audit all policies in my policies/ folder"
> "Analyze my cluster costs and suggest governance policies"
```

### Claude.ai (Web/Desktop)

1. Download and zip the `kyverno-policy-generator/` folder
2. Go to Settings > Capabilities > Skills
3. Click "Upload skill" and select the zip

---

## Example

**Input:**
> "Block any container using the latest image tag in production"

**Output — 3 files, every time:**

**1. disallow-latest-tag.yaml**
```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: disallow-latest-tag
  annotations:
    policies.kyverno.io/title: "Disallow Latest Image Tag in Production"
    policies.kyverno.io/category: "Best Practices"
    policies.kyverno.io/severity: "medium"
    policies.kyverno.io/subject: "Pod"
    policies.kyverno.io/minversion: "1.6.0"
    policies.kyverno.io/description: >-
      The ':latest' image tag is mutable and leads to unpredictable deployments
      because the underlying image can change silently. Untagged images also
      resolve to latest implicitly. This policy blocks both ':latest' and
      untagged images in production namespaces. Pin images to immutable
      versions (e.g., nginx:1.27.0) for reproducible, auditable deployments.
  labels:
    app.kubernetes.io/managed-by: kyverno-skills
    kyverno-skills/type: validate
    kyverno-skills/source: kyverno-policy-generator
spec:
  validationFailureAction: Audit
  background: true
  rules:
    # Rule 1: Require a tag — untagged images resolve to :latest implicitly
    - name: require-image-tag
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaceSelector:
                matchLabels:
                  environment: production
      validate:
        message: "All containers must use an explicit image tag. Untagged images resolve to ':latest' implicitly and are not allowed in production. Use a pinned version (e.g., nginx:1.27.0)."
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                all:
                  - key: "{{ element.image }}"
                    operator: NotEquals
                    value: "*:*"
          - list: "request.object.spec.initContainers || `[]`"
            deny:
              conditions:
                all:
                  - key: "{{ element.image }}"
                    operator: NotEquals
                    value: "*:*"
          - list: "request.object.spec.ephemeralContainers || `[]`"
            deny:
              conditions:
                all:
                  - key: "{{ element.image }}"
                    operator: NotEquals
                    value: "*:*"

    # Rule 2: Disallow the explicit :latest tag
    - name: disallow-latest-tag
      match:
        any:
          - resources:
              kinds:
                - Pod
              namespaceSelector:
                matchLabels:
                  environment: production
      validate:
        message: "The ':latest' image tag is not allowed in production. Pin all container images to a specific immutable version (e.g., nginx:1.27.0)."
        foreach:
          - list: "request.object.spec.containers"
            deny:
              conditions:
                any:
                  - key: "{{ element.image }}"
                    operator: Equals
                    value: "*:latest"
          - list: "request.object.spec.initContainers || `[]`"
            deny:
              conditions:
                any:
                  - key: "{{ element.image }}"
                    operator: Equals
                    value: "*:latest"
          - list: "request.object.spec.ephemeralContainers || `[]`"
            deny:
              conditions:
                any:
                  - key: "{{ element.image }}"
                    operator: Equals
                    value: "*:latest"
```

**2. chainsaw-test.yaml**: applies the policy, tests a compliant pod (passes), tests a non-compliant pod (blocked).

**3. test-pass.yaml + test-block.yaml**: minimal K8s resources with clear comments explaining why each passes or is blocked.

---

## Test Environment Setup

Once your policy is generated, use the scripts at the root of this repository to spin up a local test environment.

### 0. Make scripts executable

```bash
chmod u+x ../scripts/*.sh
```

### 1. Create a Minikube cluster

```bash
../scripts/minikube-cluster.sh
```

Creates a local `kyverno-lab` cluster (2 CPU, 4 GB RAM) using Docker as the driver.

### 2. Install Kyverno

```bash
../scripts/install-kyverno.sh
```

Installs Kyverno via Helm and waits for all controllers to be ready.

### 3. Install Chainsaw

**macOS:**
```bash
brew install kyverno/tap/chainsaw
```

**Linux (Ubuntu):**
```bash
CHAINSAW_VERSION=$(curl -s https://api.github.com/repos/kyverno/chainsaw/releases/latest | grep '"tag_name"' | cut -d'"' -f4)
curl -sL "https://github.com/kyverno/chainsaw/releases/download/${CHAINSAW_VERSION}/chainsaw_linux_amd64.tar.gz" | tar -xz chainsaw
sudo mv chainsaw /usr/local/bin/
```

**Verify:**
```bash
chainsaw version
```

### 4. Apply and test your policy

```bash
kubectl apply -f your-policy.yaml
chainsaw test
kubectl get policyreport -A
```

### 4. Cleanup

When you're done, remove everything with:

```bash
../scripts/cleanup.sh
```

Uninstalls Kyverno and optionally deletes the Minikube cluster.

---

## Why a Skill, not just a prompt

I tested the same prompt: "Create a Kyverno policy to require resource limits", across AI tools without the Skill.

The YAML looked correct. It had 7 production issues hidden inside:

| Issue | Consequence |
|-------|------------|
| `enforce` by default | One `kubectl apply` can cause an outage |
| Targets Deployment, not Pod | Misses StatefulSet, DaemonSet, Job, CronJob (no autogen) |
| `"*"` instead of `"?*"` | Allows empty values — defeats the purpose |
| Vague error message | "Limits required" — which container? what field? |
| No annotations | Invisible to PolicyReports, dashboards, audits |
| No Chainsaw test | Untested policy goes straight to production |
| No background scan | Existing non-compliant resources never flagged |

A Skill doesn't make the LLM smarter. It makes it disciplined.

Every guard rail in this Skill exists because I hit the wall it prevents, policies that broke clusters, autogen edge cases discovered the hard way.

---

## Requirements

- Claude Code, Claude.ai, or Claude API
- Python 3.8+ with PyYAML (`pip install pyyaml`)
- Kyverno **v1.10+** (tested on v1.15.2) — required for `foreach` + `deny` rules
- Optional: [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/) for local testing
- Optional: [Chainsaw](https://kyverno.github.io/chainsaw/) for E2E testing

> **FinOps Skill only:** OpenCost v1.120+ with MCP server enabled, Prometheus (tested with `prometheus-community/prometheus` Helm chart)

---

## Acknowledgments

- [Kyverno](https://kyverno.io/): Cloud Native Policy Management (CNCF Incubating)
- [Kyverno Policy Library](https://github.com/kyverno/policies): 200+ production-ready policies
- [Chainsaw](https://kyverno.github.io/chainsaw/): Declarative E2E testing
- [Anthropic](https://www.anthropic.com/): Claude Code and Skills platform

---

## License

CC BY-SA 4.0 — See [LICENSE](LICENSE)