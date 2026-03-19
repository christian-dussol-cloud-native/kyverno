# Kyverno Policy Patterns Catalog

Quick reference of production-ready patterns, organized by category.
Based on the official Kyverno policy library (https://github.com/kyverno/policies).

## Resource Management

### require-requests-limits
**Lib policy:** `best-practices/require-requests-limits`
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "CPU and memory requests and limits are required."
  pattern:
    spec:
      containers:
        - resources:
            requests:
              memory: "?*"
              cpu: "?*"
            limits:
              memory: "?*"
              cpu: "?*"
```

### require-requests-equal-limits (Guaranteed QoS)
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "Resources requests must equal limits for Guaranteed QoS."
  deny:
    conditions:
      any:
        - key: "{{ element.resources.requests.cpu }}"
          operator: NotEquals
          value: "{{ element.resources.limits.cpu }}"
```

### restrict-resource-quantities
**Type:** validate | **Severity:** high
```yaml
# Use foreach to check each container individually
validate:
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          any:
            - key: "{{ element.resources.limits.cpu }}"
              operator: GreaterThan
              value: "4000m"
```

## Pod Security

### disallow-privileged-containers
**Lib policy:** `pod-security/baseline/disallow-privileged-containers`
**Type:** validate | **Severity:** critical
```yaml
validate:
  message: "Privileged mode is disallowed."
  pattern:
    spec:
      containers:
        - securityContext:
            privileged: "false"
```

### disallow-host-namespaces
**Lib policy:** `pod-security/baseline/disallow-host-namespaces`
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "Sharing host namespaces is disallowed."
  pattern:
    spec:
      hostNetwork: "false"
      hostIPC: "false"
      hostPID: "false"
```

### require-run-as-nonroot
**Lib policy:** `pod-security/restricted/require-run-as-nonroot`
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "Running as root is not allowed."
  pattern:
    spec:
      securityContext:
        runAsNonRoot: true
      containers:
        - securityContext:
            runAsNonRoot: true
```

### restrict-seccomp-strict
**Lib policy:** `pod-security/restricted/restrict-seccomp-strict`
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "Seccomp profile must be RuntimeDefault or Localhost."
  pattern:
    spec:
      securityContext:
        seccompProfile:
          type: "RuntimeDefault | Localhost"
```

### disallow-capabilities
**Lib policy:** `pod-security/restricted/disallow-capabilities-strict`
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "All capabilities must be dropped."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          any:
            - key: DROP
              operator: AnyNotIn
              value: "{{ element.securityContext.capabilities.drop || `[]` }}"
```

## Image Security

### restrict-image-registries
**Lib policy:** `best-practices/restrict-image-registries`
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "Images must come from approved registries."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          all:
            - key: "{{ element.image }}"
              operator: AnyNotIn
              value:
                - "registry.company.com/*"
                - "docker.io/library/*"
```

### require-image-tag (disallow latest)
**Lib policy:** `best-practices/disallow-latest-tag`
**Type:** validate | **Severity:** medium

**Simple variant** (pattern-based, containers only):
```yaml
validate:
  message: "Using 'latest' tag is not allowed."
  pattern:
    spec:
      containers:
        - image: "!*:latest"
```

**Full variant** (foreach/deny — covers initContainers & ephemeralContainers):
```yaml
# Rule 1: Require a tag — untagged images resolve to :latest implicitly
# Use NotEquals + "*:*" to deny images that do NOT contain ":"
# IMPORTANT: message is at validate level — element.* variables are NOT available here.
# Use a static message; element.* only works inside foreach blocks (key/value/deny).
validate:
  message: "An image has no tag. Untagged images resolve to ':latest'. Specify an explicit version (e.g. nginx:1.27.0)."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          all:
            - key: "{{ element.image }}"
              operator: NotEquals   # NOTE: NotContains is NOT a valid operator
              value: "*:*"          # matches any image that has a ":" separator
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

# Rule 2: Disallow explicit :latest tag
validate:
  message: "Image uses ':latest' tag. Pin to a specific version."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          any:
            - key: "{{ element.image }}"
              operator: Equals
              value: "*:latest"
```

> **Valid operators for string matching:** `Equals`, `NotEquals` (support `*` wildcards).
> `Contains` and `NotContains` do **not** exist in Kyverno — use `Equals`/`NotEquals` with wildcards instead.

### require-image-digest
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "Images must use digest (@sha256:...) not tags."
  pattern:
    spec:
      containers:
        - image: "*@sha256:*"
```

### verify-image-cosign
**Type:** verifyImages | **Severity:** critical
```yaml
verifyImages:
  - imageReferences:
      - "registry.company.com/*"
    attestors:
      - entries:
          - keys:
              publicKeys: |-
                -----BEGIN PUBLIC KEY-----
                <your-cosign-public-key>
                -----END PUBLIC KEY-----
```

## Labels & Annotations

### require-labels
**Lib policy:** `best-practices/require-labels`
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "Label 'app.kubernetes.io/name' is required."
  pattern:
    metadata:
      labels:
        app.kubernetes.io/name: "?*"
```

### require-finops-labels
**Type:** validate | **Severity:** high | **Category:** FinOps
```yaml
validate:
  message: "FinOps labels required: team, environment, cost-center"
  pattern:
    metadata:
      labels:
        team: "?*"
        environment: "dev | qa | staging | prod"
        cost-center: "?*"
```

### add-default-labels (mutate)
**Type:** mutate | **Severity:** low
```yaml
mutate:
  patchStrategicMerge:
    metadata:
      labels:
        +(app.kubernetes.io/managed-by): "platform-team"
        +(environment): "dev"
```
Note: The `+()` prefix means "add only if not already present".

## Networking

### require-networkpolicy
**Type:** validate | **Severity:** high
```yaml
# Check that a NetworkPolicy exists in the namespace
validate:
  message: "A NetworkPolicy is required in this namespace."
  deny:
    conditions:
      - key: "{{ request.object.metadata.namespace }}"
        operator: AnyNotIn
        value: "{{ namespaces_with_netpol }}"
```

### generate-default-networkpolicy
**Type:** generate | **Severity:** medium
```yaml
generate:
  synchronize: true
  apiVersion: networking.k8s.io/v1
  kind: NetworkPolicy
  name: default-deny-ingress
  namespace: "{{request.object.metadata.name}}"
  data:
    spec:
      podSelector: {}
      policyTypes:
        - Ingress
```

## Namespace Governance

### generate-resourcequota
**Type:** generate | **Severity:** high | **Category:** FinOps
```yaml
# Auto-create ResourceQuota when namespace is created
generate:
  synchronize: true
  apiVersion: v1
  kind: ResourceQuota
  name: default-quota
  namespace: "{{request.object.metadata.name}}"
  data:
    spec:
      hard:
        requests.cpu: "4"
        requests.memory: "8Gi"
        limits.cpu: "8"
        limits.memory: "16Gi"
```

### generate-limitrange
**Type:** generate | **Severity:** medium | **Category:** FinOps
```yaml
generate:
  synchronize: true
  apiVersion: v1
  kind: LimitRange
  name: default-limitrange
  namespace: "{{request.object.metadata.name}}"
  data:
    spec:
      limits:
        - default:
            cpu: "500m"
            memory: "512Mi"
          defaultRequest:
            cpu: "100m"
            memory: "128Mi"
          type: Container
```

## RBAC & Multi-Tenancy

### restrict-clusterrole-binding
**Type:** validate | **Severity:** critical
```yaml
validate:
  message: "ClusterRoleBindings to cluster-admin are restricted."
  deny:
    conditions:
      all:
        - key: "{{ request.object.roleRef.name }}"
          operator: Equals
          value: "cluster-admin"
```

### restrict-wildcard-verbs
**Type:** validate | **Severity:** high
```yaml
validate:
  message: "Wildcard verbs in Roles are not allowed."
  foreach:
    - list: "request.object.rules"
      deny:
        conditions:
          any:
            - key: "*"
              operator: AnyIn
              value: "{{ element.verbs }}"
```

## Probes & Reliability

### require-probes
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "Liveness and readiness probes are required."
  pattern:
    spec:
      containers:
        - livenessProbe:
            periodSeconds: ">0"
          readinessProbe:
            periodSeconds: ">0"
```

### require-pod-disruption-budget
**Type:** validate | **Severity:** medium
```yaml
# Typically implemented as a generate policy that creates
# a PDB when a Deployment with replicas > 1 is created
generate:
  synchronize: true
  apiVersion: policy/v1
  kind: PodDisruptionBudget
  name: "{{request.object.metadata.name}}-pdb"
  namespace: "{{request.object.metadata.namespace}}"
  data:
    spec:
      minAvailable: 1
      selector:
        matchLabels:
          app: "{{request.object.metadata.name}}"
```

## Storage

### restrict-volume-types
**Lib policy:** `pod-security/restricted/restrict-volume-types`
**Type:** validate | **Severity:** medium
```yaml
validate:
  message: "Only configMap, emptyDir, projected, secret, downwardAPI, PVC, and ephemeral volumes are allowed."
  deny:
    conditions:
      all:
        - key: "{{ element.keys(@)[?!contains(@, 'name')] }}"
          operator: AnyNotIn
          value:
            - configMap
            - emptyDir
            - projected
            - secret
            - downwardAPI
            - persistentVolumeClaim
            - ephemeral
```

## FinOps-Specific (Custom — Not in Official Lib)

### enforce-max-cpu-per-pod
**Type:** validate | **Severity:** high | **Category:** FinOps
```yaml
validate:
  message: "Container CPU limit exceeds FinOps max of 4 cores. Request exception."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          any:
            - key: "{{ element.resources.limits.cpu }}"
              operator: GreaterThan
              value: "4000m"
```

### enforce-spot-for-non-prod
**Type:** validate | **Severity:** medium | **Category:** FinOps
```yaml
# Require nodeSelector for spot instances in non-prod namespaces
validate:
  message: "Non-production workloads must run on spot/preemptible nodes."
  pattern:
    spec:
      nodeSelector:
        kubernetes.io/lifecycle: "spot | preemptible"
```

### restrict-pv-size
**Type:** validate | **Severity:** medium | **Category:** FinOps
```yaml
validate:
  message: "PVC size exceeds maximum of 100Gi. Request exception for larger volumes."
  pattern:
    spec:
      resources:
        requests:
          storage: "<=100Gi"
```
