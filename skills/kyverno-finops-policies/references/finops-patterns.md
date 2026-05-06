# FinOps Governance Patterns

Tested patterns for Kubernetes cost governance with Kyverno.

## Pattern 1: Tiered Resource Limits

Enforce different resource limits per environment tier.

| Tier | Max CPU | Max Memory | Use Case |
|------|---------|------------|----------|
| dev | 2 cores | 4Gi | Development and testing |
| staging | 4 cores | 8Gi | Pre-production validation |
| prod | 8 cores | 16Gi | Production workloads |

Above prod limits (e.g., >8 cores CPU) requires a justification annotation:
`finops.kyverno.io/justification: "ML training workload, approved by budget-owner"`

Use `assets/templates/tiered-limits-base.yaml`.

## Pattern 2: Cost-Allocation Label Enforcement

Required labels for FinOps reporting and chargeback:

| Label | Purpose | Example |
|-------|---------|---------|
| `team` | Who owns this resource? | `team: payments` |
| `cost-center` | Which budget pays? | `cost-center: CC-4521` |
| `environment` | Which tier? | `environment: production` |
| `service` | Which business service? | `service: checkout-api` |

Optional but recommended:

| Label | Purpose | Example |
|-------|---------|---------|
| `budget-owner` | Who approves costs? | `budget-owner: jane.smith` |
| `project` | Which initiative? | `project: platform-migration` |

Use `assets/templates/cost-labels-base.yaml`.

## Pattern 3: Over-Provisioning Guard Rails

Block pods requesting excessive resources without justification.

Thresholds:
- CPU request > 4 cores → require `finops.kyverno.io/justification` annotation
- Memory request > 8Gi → require `finops.kyverno.io/justification` annotation

The justification annotation must be non-empty and describe why the resource
request exceeds standard limits.

Use `assets/templates/overprovision-guard-base.yaml`.

## Pattern 4: FOCUS Compliant Tagging

Generate labels that map to the FinOps Open Cost and Usage Specification (FOCUS).

| FOCUS Dimension | Kubernetes Label | Description |
|-----------------|-----------------|-------------|
| ServiceName | `service` | Business service name |
| ResourceType | Derived from `kind` | Kubernetes resource type |
| ChargeCategory | `cost-center` | Cost allocation category |
| CommitmentDiscountType | `spot-eligible` | Spot/preemptible eligibility |

## Pattern 5: Budget-Aware Policies

Policies that enforce budget constraints:
- Maximum total CPU per namespace (e.g., dev namespaces capped at 16 cores total)
- Require ResourceQuota alongside namespace creation
- Alert when namespace resource usage exceeds 80% of quota
