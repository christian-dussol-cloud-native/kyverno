# Complete Testing Guide - Kyverno Policies

This guide allows you to test all policies in your local cluster and get familiar with.

## 📋 Prerequisites

- Kubernetes cluster (minikube, kind, k3s, or real cluster)
- kubectl configured
- Admin rights on the cluster

## 🚀 Installing Kyverno

```bash
# Install Kyverno
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno
```

**Expected result:**
```
NAME                                             READY   STATUS    RESTARTS   AGE
kyverno-admission-controller-xxx                 1/1     Running   0          2m
kyverno-background-controller-xxx                1/1     Running   0          2m
kyverno-cleanup-controller-xxx                   1/1     Running   0          2m
kyverno-reports-controller-xxx                   1/1     Running   0          2m
```

## 📝 Test 1: Detect Ingress NGINX

### Deploy the detection policy

```bash
kubectl apply -f policies/detect-ingress-nginx.yaml
```

**Expected result:**
```
clusterpolicy.kyverno.io/detect-ingress-nginx created
```

### Create test resources

```bash
kubectl apply -f tests/test-ingress-nginx.yaml
```

**Note:** If the block-new-ingress-nginx policy is already active, some resources will be blocked. This is normal.

### Check policy reports

```bash
# View all reports
kubectl get policyreport -n default

# Detailed view of violations
kubectl get policyreport -n default -o wide
```

**Expected result:**
- You should see violations for Ingress resources with nginx
- Each violation mentions "Migration to Gateway API required"

### Cleanup

```bash
kubectl delete -f tests/test-ingress-nginx.yaml
kubectl delete clusterpolicy detect-ingress-nginx
```

---

## 🚫 Test 2: Block New Ingress NGINX

### Deploy the blocking policy

```bash
kubectl apply -f policies/block-new-ingress-nginx.yaml
```

### Try to create an Ingress NGINX (MUST FAIL)

```bash
kubectl apply -f tests/test-ingress-nginx.yaml
```

**Expected result:**
```
Error from server: error when creating "tests/test-ingress-nginx.yaml": 
admission webhook "validate.kyverno.svc-fail" denied the request: 

policy Ingress/default/test-nginx-classname for resource violation: 

block-nginx-ingress-class:
  Ingress NGINX is deprecated and will be retired in March 2026.
  New resources using Ingress NGINX are not allowed.
  
  Please use Gateway API instead: https://gateway-api.sigs.k8s.io/
```

✅ **This is exactly what we want!** The policy blocks new creations.

### Test exception

Modify the `test-ingress-nginx.yaml` file to add the exception annotation:

```bash
# Apply only the resource with exception
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: test-nginx-exception
  namespace: default
  annotations:
    kubernetes.io/ingress.class: nginx
    migration.kyverno.io/allow-nginx: "true"
    migration.reason: "Test exception - will migrate Q1 2025"
spec:
  rules:
  - host: test-exception.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: test-service
            port:
              number: 80
EOF
```

**Expected result:**
```
ingress.networking.k8s.io/test-nginx-exception created
```

✅ **The exception works!** The resource with annotation passes.

### Cleanup

```bash
kubectl delete ingress test-nginx-exception -n default
kubectl delete clusterpolicy block-new-ingress-nginx
```

---

## 🔍 Test 3: Audit All Ingress

### Deploy the audit policy

```bash
kubectl apply -f policies/audit-all-ingress.yaml
```

### Create different types of ingress

```bash
# Create services first
kubectl apply -f tests/test-ingress-nginx.yaml
kubectl apply -f tests/test-ingress-other.yaml
```

### Check categorization

```bash
# View all reports with categories
kubectl get policyreport -n default -o yaml | grep "Category:"
```

**Expected result:**
```
message: 'Category: nginx-ingress | Status: Migration Required ...'
message: 'Category: other-controller | Status: Alternative Implementation ...'
```

### Count by category

```bash
kubectl get policyreport -n default -o yaml | \
  grep "Category:" | \
  sort | uniq -c
```

**Expected result:**
```
      3 Category: nginx-ingress
      2 Category: other-controller
```

### Cleanup

```bash
kubectl delete -f tests/test-ingress-nginx.yaml
kubectl delete -f tests/test-ingress-other.yaml
kubectl delete clusterpolicy audit-all-ingress
```

---

## ✅ Test 4: Require Gateway API

### Prepare the namespace

```bash
# Create a namespace for testing
kubectl create namespace test-gateway-enforcement

# Label it to activate enforcement
kubectl label namespace test-gateway-enforcement migration-phase=gateway-api-required
```

### Deploy the policy

```bash
kubectl apply -f policies/require-gateway-api.yaml
```

### Try to create a traditional Ingress (MUST GENERATE A WARNING)

```bash
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: test-traditional
  namespace: test-gateway-enforcement
spec:
  ingressClassName: traefik
  rules:
  - host: test.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: test-service
            port:
              number: 80
EOF
```

**In Audit mode (default):**
- The resource is created
- A warning is generated in policy reports

**Check warnings:**
```bash
kubectl get policyreport -n test-gateway-enforcement -o yaml | grep "gateway-api"
```

### Switch to Enforce mode (optional)

```bash
kubectl patch clusterpolicy require-gateway-api \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/validationFailureAction", "value":"Enforce"}]'
```

Now try to create the traditional Ingress → **MUST BE BLOCKED**

### Cleanup

```bash
kubectl delete namespace test-gateway-enforcement
kubectl delete clusterpolicy require-gateway-api
```

---

## 🌐 Optional Test: Gateway API (HTTPRoute)

**This test is OPTIONAL** - It only serves to show what Gateway API looks like.

### Why is it optional?

The 4 Kyverno policies work **perfectly WITHOUT** Gateway API CRDs. This test is purely educational to show the recommended migration target.

### Prerequisites

Gateway API CRDs must be installed:

```bash
# Install Gateway API CRDs
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.2.0/standard-install.yaml

# Wait for CRDs to be ready
kubectl wait --for condition=established --timeout=60s crd/gateways.gateway.networking.k8s.io
kubectl wait --for condition=established --timeout=60s crd/httproutes.gateway.networking.k8s.io
```

### Test HTTPRoute

```bash
# 1. Deploy the Gateway API example
kubectl apply -f tests/test-httproute.yaml

# 2. Verify Gateway API resources
kubectl get gateway,httproute -n default

# 3. View details
kubectl describe httproute test-httproute -n default
```

**Expected result:**
```
NAME                                        HOSTNAMES                      AGE
httproute.gateway.networking.k8s.io/test-httproute   ["test-gateway-api.example.com"]   10s
```

### Cleanup

```bash
kubectl delete -f tests/test-httproute.yaml
```

---

## 📊 Understanding Policy Reports

After deploying policies, view results:

```bash
# List all policy reports
kubectl get policyreport -A

# View detailed report for a namespace
kubectl get policyreport -n default -o yaml

# Count violations by type
kubectl get policyreport -A -o yaml | \
  grep -E "(result:)" | \
  sort | uniq -c
```

## 🔄 Progressive Rollout Strategy

### Phase 1: Detection (Week 1)
```bash
# Deploy detection policy
kubectl apply -f policies/detect-ingress-nginx.yaml

# Inventory your usage
kubectl get policyreport -A
```

### Phase 2: Audit (Week 2-3)
```bash
# Deploy comprehensive audit
kubectl apply -f policies/audit-all-ingress.yaml

# Analyze all ingress types
kubectl get policyreport -A -o yaml | grep "Category:"
```

### Phase 3: Prevention (Week 4+)
```bash
# Block new Ingress NGINX resources
kubectl apply -f policies/block-new-ingress-nginx.yaml

# Existing resources still work, new ones blocked
```

### Phase 4: Enforcement (After migration)
```bash
# Enforce Gateway API for new resources
kubectl apply -f policies/require-gateway-api.yaml

# Switch to Enforce mode when ready
kubectl patch clusterpolicy require-gateway-api \
  --type='json' \
  -p='[{"op": "replace", "path": "/spec/validationFailureAction", "value":"Enforce"}]'
```

## 📖 Resources

**Official Announcements:**
- [Ingress NGINX Retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [Gateway API Documentation](https://gateway-api.sigs.k8s.io/)

**Migration Guides:**
- [Migrating from Ingress to Gateway API](https://gateway-api.sigs.k8s.io/guides/migrating-from-ingress/)
- [Kyverno Documentation](https://kyverno.io/docs/)


## 🐛 Troubleshooting

### Issue: Kyverno doesn't start

```bash
# Check events
kubectl get events -n kyverno --sort-by='.lastTimestamp'

# Check logs
kubectl logs -n kyverno -l app.kubernetes.io/name=kyverno
```

### Issue: Policy reports don't appear

```bash
# Wait for Kyverno to process resources (may take 30 seconds)
sleep 30
kubectl get policyreport -A

# Check background controller
kubectl logs -n kyverno -l app.kubernetes.io/component=background-controller
```

### Issue: Policies don't block

```bash
# Verify validationFailureAction is "Enforce"
kubectl get clusterpolicy block-new-ingress-nginx -o yaml | grep validationFailureAction

# Check webhooks
kubectl get validatingwebhookconfigurations | grep kyverno
```

### Issue: Policy reports take too long

**This is normal!** Kyverno's background controller may take 15-30 seconds to generate policy reports, especially on:
- First startup
- Slow clusters  
- Busy systems

**Solution:** Simply wait longer (up to 1 minute) after creating resources.