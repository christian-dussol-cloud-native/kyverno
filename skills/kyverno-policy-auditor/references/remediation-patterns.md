# Remediation Patterns

Ready-to-use YAML snippets for the most common audit findings.

## Add Missing Annotations

```yaml
metadata:
  annotations:
    policies.kyverno.io/title: "<Descriptive title>"
    policies.kyverno.io/category: "<Best Practices|Security|Resource Management|FinOps|Networking>"
    policies.kyverno.io/severity: "<low|medium|high|critical>"
    policies.kyverno.io/subject: "<Pod|Deployment|Service|Namespace>"
    policies.kyverno.io/minversion: "1.6.0"
    policies.kyverno.io/description: >-
      Clear description of what the policy does and why.
      Include the business reason, not just the technical rule.
```

## Add Managed-By Label

```yaml
metadata:
  labels:
    app.kubernetes.io/managed-by: kyverno
```

## Switch from Enforce to Audit

```yaml
spec:
  validationFailureAction: Audit  # Changed from Enforce — review PolicyReports first
```

## Fix Autogen: Deployment → Pod

```yaml
# BEFORE (limited to Deployments only)
match:
  resources:
    kinds:
      - Deployment

# AFTER (autogen covers Deployment, StatefulSet, DaemonSet, Job, CronJob)
match:
  any:
    - resources:
        kinds:
          - Pod
```

## Fix Pattern: "*" → "?*"

```yaml
# BEFORE (allows empty values)
pattern:
  spec:
    containers:
      - resources:
          limits:
            memory: "*"

# AFTER (requires non-empty value)
pattern:
  spec:
    containers:
      - resources:
          limits:
            memory: "?*"
```

## Add background: true

```yaml
spec:
  validationFailureAction: Audit
  background: true  # Scan existing resources, not just new admissions
```

## Improve Error Message

```yaml
# BEFORE
validate:
  message: "Limits required"

# AFTER
validate:
  message: >-
    Container '{{ element.name }}' in Pod '{{ request.object.metadata.name }}'
    is missing required memory limits. Add resources.limits.memory to all
    containers. See: https://kyverno.io/policies/best-practices/
```

## Fix forEach Variable Scope

```yaml
# WRONG — element.* is not available in message at validate level
validate:
  message: "Image '{{ element.image }}' is invalid."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          all:
            - key: "{{ element.image }}"
              operator: Equals
              value: "*:latest"

# CORRECT — static message at validate level, element.* only inside foreach
validate:
  message: "One or more container images are invalid. Check all containers."
  foreach:
    - list: "request.object.spec.containers"
      deny:
        conditions:
          all:
            - key: "{{ element.image }}"
              operator: Equals
              value: "*:latest"
```

## Fix Invalid Operator

```yaml
# WRONG — Contains does not exist in Kyverno
conditions:
  all:
    - key: "{{ element.image }}"
      operator: Contains
      value: "latest"

# CORRECT — use Equals with wildcard pattern
conditions:
  all:
    - key: "{{ element.image }}"
      operator: Equals
      value: "*:latest"
```
