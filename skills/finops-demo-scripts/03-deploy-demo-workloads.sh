#!/bin/bash
# 03-deploy-demo-workloads.sh
# Deploys sample workloads so OpenCost has something to measure.

set -e

echo "📂 Creating demo namespaces with environment labels..."

kubectl create namespace dev-team-a 2>/dev/null || echo "  dev-team-a already exists"
kubectl label namespace dev-team-a environment=dev --overwrite

kubectl create namespace prod-payments 2>/dev/null || echo "  prod-payments already exists"
kubectl label namespace prod-payments environment=production --overwrite

echo ""
echo "🔥 Deploying intentionally over-provisioned pod in dev (creates measurable waste)..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: waste-test
  namespace: dev-team-a
  labels:
    app: waste-test
    team: dev-team-a
    cost-center: engineering
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    resources:
      requests:
        cpu: "2"
        memory: "2Gi"
      limits:
        cpu: "4"
        memory: "4Gi"
EOF

echo ""
echo "✅ Deploying properly-sized pod in prod..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: prod-test
  namespace: prod-payments
  labels:
    app: prod-test
    team: prod-payments
    cost-center: payments
spec:
  containers:
  - name: nginx
    image: nginx:1.27
    resources:
      requests:
        cpu: "200m"
        memory: "256Mi"
      limits:
        cpu: "500m"
        memory: "512Mi"
EOF

echo ""
echo "✅ Demo workloads deployed."
kubectl get pods -n dev-team-a
kubectl get pods -n prod-payments

echo ""
echo "⏳ IMPORTANT: OpenCost needs ~15-20 minutes to collect meaningful allocation data."
echo "   Monitor with: ./03b-wait-for-data.sh (exits automatically when ready)"
echo "   UI (optional): kubectl port-forward -n opencost svc/opencost 9090:9090 → http://localhost:9090"
echo ""
echo "Next step (after waiting): ./04-connect-mcp.sh"
