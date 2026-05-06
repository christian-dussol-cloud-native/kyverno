# FOCUS Mapping

Mapping between FOCUS (FinOps Open Cost and Usage Specification) dimensions
and Kubernetes labels/annotations for Kyverno policies.

## What is FOCUS?

FOCUS is an open specification by the FinOps Foundation that standardizes
cost and usage data across cloud providers. By mapping Kubernetes labels
to FOCUS dimensions, cost reports become consistent and comparable.

## Mapping Table

| FOCUS Dimension | Kubernetes Source | Policy Enforcement |
|-----------------|------------------|--------------------|
| ServiceName | Label `service` | Required on all Pods |
| SubAccountName | Label `team` or namespace name | Required on all Pods |
| ResourceType | `kind` (Pod, Deployment, etc.) | Auto-derived |
| ChargeCategory | Label `cost-center` | Required on all Pods |
| CommitmentDiscountType | Label `spot-eligible` | Optional |
| Region | Node label `topology.kubernetes.io/region` | Auto-derived |
| AvailabilityZone | Node label `topology.kubernetes.io/zone` | Auto-derived |

## Policy Annotations for FOCUS

Add these annotations to FinOps policies for traceability:

```yaml
annotations:
  finops.kyverno.io/service-name: "<service this policy governs>"
  finops.kyverno.io/charge-category: "<cost center or budget category>"
  finops.kyverno.io/resource-type: "Pod"
```

## Why This Matters

Without FOCUS-compliant labels, cost reports from different clusters
or cloud providers use different schemas. FinOps teams spend hours
reconciling data manually. FOCUS-compliant Kyverno policies ensure
every resource is tagged consistently from the moment it's created.
