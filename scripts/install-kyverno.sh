#!/bin/bash
set -euo pipefail

# =============================================================================
# Install Kyverno — Kyverno Lab
# =============================================================================
# Installs Kyverno on the current cluster via Helm.
# Run this after minikube-cluster.sh.
# =============================================================================

KYVERNO_NAMESPACE="kyverno"
KYVERNO_VERSION="3.2.6"   # https://github.com/kyverno/kyverno/releases

echo "Installing Kyverno $KYVERNO_VERSION..."

# Check prerequisites
for cmd in kubectl helm; do
  if ! command -v $cmd &> /dev/null; then
    echo "$cmd not found. Please install it first."
    exit 1
  fi
done

# Add Kyverno Helm repo
echo ""
echo "Adding Kyverno Helm repository..."
helm repo add kyverno https://kyverno.github.io/kyverno/ 2>/dev/null || true
helm repo update

# Create namespace
kubectl create namespace $KYVERNO_NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Install Kyverno
echo ""
echo "Installing Kyverno (this may take a few minutes)..."
helm upgrade --install kyverno kyverno/kyverno \
  -n $KYVERNO_NAMESPACE \
  --version $KYVERNO_VERSION

echo ""
echo "Kyverno is being installed. Monitor progress in another terminal:"
echo ""
echo "  kubectl get pods -n $KYVERNO_NAMESPACE -w"
echo ""
echo "Once all pods show Running, you can apply your policy:"
echo "  kubectl apply -f your-policy.yaml"
echo ""
echo "Check PolicyReports:"
echo "  kubectl get policyreport -A"
