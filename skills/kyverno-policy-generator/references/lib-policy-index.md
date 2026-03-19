# Kyverno Official Policy Library Index

Source: https://github.com/kyverno/policies
Website: https://kyverno.io/policies/

Use this index to find existing policies before generating from scratch.
When a match exists, customize rather than recreate.

## Pod Security Admission (PSA)

### Baseline Level
| Policy | Description | Kinds |
|--------|-------------|-------|
| disallow-capabilities | Restrict added Linux capabilities | Pod |
| disallow-host-namespaces | Block hostNetwork, hostIPC, hostPID | Pod |
| disallow-host-path | Block hostPath volume mounts | Pod |
| disallow-host-ports | Restrict hostPort usage | Pod |
| disallow-host-process | Block Windows hostProcess | Pod |
| disallow-privileged-containers | Block privileged: true | Pod |
| disallow-proc-mount | Restrict /proc mount types | Pod |
| disallow-selinux | Restrict SELinux options | Pod |

### Restricted Level
| Policy | Description | Kinds |
|--------|-------------|-------|
| disallow-capabilities-strict | Drop ALL, allow only NET_BIND_SERVICE | Pod |
| require-run-as-non-root-user | Enforce runAsUser != 0 | Pod |
| require-run-as-nonroot | Enforce runAsNonRoot: true | Pod |
| restrict-seccomp-strict | Require RuntimeDefault/Localhost | Pod |
| restrict-volume-types | Allow only safe volume types | Pod |

## Best Practices
| Policy | Description | Kinds |
|--------|-------------|-------|
| disallow-latest-tag | Block :latest image tag | Pod |
| require-labels | Require standard K8s labels | Pod, Deployment |
| require-probes | Require liveness/readiness | Pod |
| require-requests-limits | Require CPU/memory requests+limits | Pod |
| restrict-image-registries | Allowlist image registries | Pod |
| disallow-default-namespace | Block deployments to default ns | Pod, Deployment |
| require-pod-disruption-budget | Require PDB for HA | Deployment |
| require-ro-rootfs | Require readOnlyRootFilesystem | Pod |

## CIS Kubernetes Benchmark
| Policy | CIS Control | Description |
|--------|-------------|-------------|
| restrict-automount-sa-token | 5.1.6 | Don't auto-mount SA tokens |
| restrict-binding-clusteradmin | 5.1.1 | Restrict cluster-admin binding |
| restrict-wildcard-resources | 5.1.3 | Block wildcard in RBAC |
| restrict-wildcard-verbs | 5.1.3 | Block wildcard verbs |
| require-network-policy | 5.3.2 | Require NetworkPolicy per ns |
| restrict-default-sa | 5.1.5 | Restrict default ServiceAccount |

## NIST SP 800-53
| Policy | NIST Control | Description |
|--------|-------------|-------------|
| require-encryption-at-rest | SC-28 | Enforce encrypted secrets |
| restrict-external-ips | AC-4 | Block external IP in Services |
| require-labels-audit | AU-3 | Labels for audit trail |
| restrict-nodeport | AC-4 | Block NodePort services |

## Networking
| Policy | Description | Kinds |
|--------|-------------|-------|
| restrict-external-ips | Block externalIPs in Services | Service |
| restrict-loadbalancer | Restrict LoadBalancer usage | Service |
| restrict-nodeport | Block NodePort services | Service |
| require-networkpolicy | Require NetworkPolicy exists | Namespace |

## Resource Management
| Policy | Description | Kinds |
|--------|-------------|-------|
| require-requests-limits | Require resource requests+limits | Pod |
| restrict-escalation | Block privilege escalation | Pod |
| restrict-sysctls | Restrict unsafe sysctls | Pod |
| restrict-apparmor | Require AppArmor profile | Pod |

## Image Security & Supply Chain
| Policy | Description | Kinds |
|--------|-------------|-------|
| verify-image | Verify cosign signatures | Pod |
| verify-attestation | Verify SLSA attestations | Pod |
| check-image-digest | Require image digest not tag | Pod |
| restrict-image-registries | Allowlist registries | Pod |

## Multi-Tenancy
| Policy | Description | Kinds |
|--------|-------------|-------|
| restrict-annotations | Block certain annotations | Pod |
| restrict-namespace-creation | Restrict who creates ns | Namespace |
| restrict-binding-clusteradmin | Block cluster-admin bind | ClusterRoleBinding |
| generate-namespace-quota | Auto-create quotas | Namespace |

## Custom (Not in Official Library — Kyverno Skills Originals)

These patterns are unique to the Kyverno Skills pack:

| Policy | Category | Description |
|--------|----------|-------------|
| require-finops-labels | FinOps | team + environment + cost-center |
| enforce-max-cpu-per-pod | FinOps | Cap CPU at N cores per container |
| enforce-max-memory-per-pod | FinOps | Cap memory at N Gi per container |
| enforce-spot-for-non-prod | FinOps | Spot/preemptible for non-prod |
| restrict-pv-size | FinOps | Max PVC storage size |
| generate-tiered-quotas | FinOps | Tier-based ResourceQuota (dev/prod) |
| restrict-node-size | FinOps | Block oversized node types |
| generate-namespace-budget | FinOps | Full 4-layer governance setup |

## How to Use This Index

1. Search by category or keyword for the user's intent
2. If match found → reference it: "Based on the official Kyverno policy `<name>`"
3. Load the specific pattern from `references/policy-patterns.md`
4. Customize with user's specific parameters (namespaces, values, labels)
5. Generate Chainsaw tests alongside

## Library Stats
- **200+** policies in the official library
- **Categories:** 15+ (PSA, CIS, NIST, best-practices, networking, etc.)
- **Tested:** All policies have CLI test cases in the repository
- **Maintained:** Active CNCF incubating project
- **License:** Apache 2.0
