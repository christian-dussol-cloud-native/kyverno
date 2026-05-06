#!/bin/bash
# 02-install-opencost.sh
# Installs Prometheus then OpenCost (CNCF Sandbox project) on the cluster.

set -e

echo "📦 Adding Helm repos..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add opencost https://opencost.github.io/opencost-helm-chart
helm repo update

echo ""
echo "📦 Installing Prometheus in prometheus-system namespace..."
helm install prometheus prometheus-community/prometheus \
  --namespace prometheus-system \
  --create-namespace

echo ""
echo "⏳ Waiting for Prometheus server to be ready (up to 3 minutes)..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=prometheus,app.kubernetes.io/component=server \
  -n prometheus-system \
  --timeout=180s

echo ""
echo "📦 Installing OpenCost in opencost namespace..."
helm install opencost opencost/opencost \
  --namespace opencost \
  --create-namespace \
  --set opencost.prometheus.internal.serviceName=prometheus-server \
  --set opencost.prometheus.internal.namespaceName=prometheus-system

echo ""
echo "⏳ Waiting for OpenCost pod to be ready (up to 2 minutes)..."
kubectl wait --for=condition=ready pod \
  -l app.kubernetes.io/name=opencost \
  -n opencost \
  --timeout=120s

echo ""
echo "✅ Prometheus and OpenCost installed and ready."
kubectl get pods -n prometheus-system
kubectl get pods -n opencost

echo ""
echo "Next step: ./03-deploy-demo-workloads.sh"
