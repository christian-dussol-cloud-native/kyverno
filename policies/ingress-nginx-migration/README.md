# Kyverno Policies for Ingress NGINX Migration

Automated detection and governance for migrating from Ingress NGINX to Gateway API before the March 2026 retirement deadline.

## 🚨 Context

**Kubernetes SIG Network announced on November 12, 2025** that Ingress NGINX will be retired in March 2026. After this date:
- ❌ No new releases
- ❌ No security patches
- ❌ No bug fixes

**This repository provides 4 Kyverno policies to help you:**
- Detect existing Ingress NGINX usage
- Prevent new Ingress NGINX deployments
- Audit all ingress resources
- Enforce Gateway API adoption

## 📦 The 4 Policies

### 1. detect-ingress-nginx.yaml
**Purpose:** Detect all Ingress NGINX resources across your clusters

**Mode:** Audit (non-blocking)

**What it does:**
- Scans all Ingress resources
- Identifies those using `ingressClassName: nginx` or annotation `kubernetes.io/ingress.class: nginx`
- Generates policy reports for visibility

**Result:** Policy report showing all Ingress NGINX resources

---

### 2. block-new-ingress-nginx.yaml
**Purpose:** Prevent creation of new Ingress NGINX resources

**Mode:** Enforce (blocking)

**What it does:**
- Blocks creation of new Ingress resources using Ingress NGINX
- Allows exceptions via annotation `migration.kyverno.io/allow-nginx: "true"`
- Provides clear error message with migration guidance

**Result:** New Ingress NGINX resources are rejected

---

### 3. audit-all-ingress.yaml
**Purpose:** Comprehensive audit of all ingress resources

**Mode:** Audit (non-blocking)

**What it does:**
- Categorizes ALL ingress resources in cluster:
  - `nginx-ingress` - Requires migration
  - `gateway-api` - Already using Gateway API
  - `other-controller` - Using alternative controllers

**Result:** Complete inventory categorized by type

---

### 4. require-gateway-api.yaml
**Purpose:** Enforce Gateway API adoption for new resources

**Mode:** Configurable (Audit or Enforce)

**What it does:**
- Ensures new ingress traffic uses Gateway API (HTTPRoute, etc.)
- Supports progressive rollout by namespace
- Can be switched from Audit to Enforce mode

**Result:** New traffic routing must use Gateway API

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Kubernetes cluster (1.26+)
- kubectl configured
- Admin access to install policies

### Step 1: Install Kyverno

```bash
helm repo add kyverno https://kyverno.github.io/kyverno/
helm repo update
helm install kyverno kyverno/kyverno
```

### Step 2: Deploy Detection Policy

```bash
kubectl apply -f policies/detect-ingress-nginx.yaml
```

### Step 3: View Results

```bash
# View policy reports
kubectl get policyreport -A

# Detailed view of violations
kubectl get policyreport -A -o wide
```

## 📁 Repository Structure

```
.
├── policies/
│   ├── detect-ingress-nginx.yaml      # Policy 1: Detection
│   ├── block-new-ingress-nginx.yaml   # Policy 2: Prevention
│   ├── audit-all-ingress.yaml         # Policy 3: Audit
│   └── require-gateway-api.yaml       # Policy 4: Enforcement
│
├── tests/
│   ├── test-ingress-nginx.yaml        # Test ingress with nginx
│   ├── test-ingress-gateway-api.yaml  # Test with Gateway API
│   ├── test-ingress-other.yaml        # Test with other controller
│   └── test-httproute.yaml            # Test Gateway API HTTPRoute
│
└── README.md
```

## 🧪 Testing the Policies

### Test 1: Detect Existing Ingress NGINX

```bash
# Deploy a test Ingress with nginx
kubectl apply -f tests/test-ingress-nginx.yaml

# Check policy report
kubectl get policyreport -n default

# Expected: Policy report shows violation for nginx ingress
```

### Test 2: Block New Ingress NGINX

```bash
# First, deploy the blocking policy
kubectl apply -f policies/block-new-ingress-nginx.yaml

# Try to create a new Ingress with nginx
kubectl apply -f tests/test-ingress-nginx.yaml

# Expected: Request is blocked with error message
```

### Test 3: Audit All Ingress Types

```bash
# Deploy the audit policy
kubectl apply -f policies/audit-all-ingress.yaml

# Deploy test ingresses of different types
kubectl apply -f tests/test-ingress-nginx.yaml
kubectl apply -f tests/test-ingress-other.yaml
kubectl apply -f tests/test-httproute.yaml

# View categorized results
kubectl get policyreport -n default -o yaml | grep "Category:"

# Expected: Reports showing nginx-ingress, gateway-api, and other-controller
```

### Test 4: Enforce Gateway API

```bash
# Deploy enforcement policy in Audit mode first
kubectl apply -f policies/require-gateway-api.yaml

# Try creating traditional Ingress
kubectl apply -f tests/test-ingress-nginx.yaml

# Check warnings in policy report
kubectl get policyreport -n default

# Expected: Audit report recommending Gateway API
```

## 📊 Understanding Policy Reports

After deploying policies, view results:

```bash
# List all policy reports
kubectl get policyreport -A

# View detailed report for a namespace
kubectl get policyreport -n default -o yaml

## 📖 Resources

**Official Announcements:**
- [Ingress NGINX Retirement](https://kubernetes.io/blog/2025/11/11/ingress-nginx-retirement/)
- [Gateway API Documentation](https://gateway-api.sigs.k8s.io/)

**Migration Guides:**
- [Migrating from Ingress to Gateway API](https://gateway-api.sigs.k8s.io/guides/migrating-from-ingress/)
- [Kyverno Documentation](https://kyverno.io/docs/)
