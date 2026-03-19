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

> More Skills are in development, including policy auditing and FinOps cost governance.
>
> Want to understand how each file works under the hood? See [architecture.md](kyverno-policy-generator/references/architecture.md).

---

## Quick Start

### Claude Code (Terminal)

```bash
# Clone the repo
git clone https://github.com/christian-dussol-cloud-native/kyverno/
cd kyverno/skills

# Install the Skill
mkdir -p ~/.claude/skills/
cp -r kyverno-policy-generator ~/.claude/skills/

# Launch Claude Code in your terminal
claude

# The Skill triggers automatically on relevant prompts
> "Block any container using the latest image tag in production"
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
chmod u+x ./scripts/*.sh
```

### 1. Create a Minikube cluster

```bash
./scripts/minikube-cluster.sh
```

Creates a local `kyverno-lab` cluster (2 CPU, 4 GB RAM) using Docker as the driver.

### 2. Install Kyverno

```bash
./scripts/install-kyverno.sh
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
./scripts/cleanup.sh
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
- Optional: [Kyverno CLI](https://kyverno.io/docs/kyverno-cli/) for local testing
- Optional: [Chainsaw](https://kyverno.github.io/chainsaw/) for E2E testing

---

## Acknowledgments

- [Kyverno](https://kyverno.io/): Cloud Native Policy Management (CNCF Incubating)
- [Kyverno Policy Library](https://github.com/kyverno/policies): 200+ production-ready policies
- [Chainsaw](https://kyverno.github.io/chainsaw/): Declarative E2E testing
- [Anthropic](https://www.anthropic.com/): Claude Code and Skills platform

---

## License

CC BY-SA 4.0 — See [LICENSE](LICENSE)