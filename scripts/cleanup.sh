#!/bin/bash
set -euo pipefail

# =============================================================================
# Cleanup — Kyverno Lab
# =============================================================================
# Removes Kyverno and optionally deletes the Minikube cluster.
# =============================================================================

CLUSTER_NAME="kyverno-lab"
KYVERNO_NAMESPACE="kyverno"

echo "Cleaning up Kyverno Lab..."

# Remove Kyverno
echo ""
echo "Removing Kyverno..."
helm uninstall kyverno -n $KYVERNO_NAMESPACE --no-hooks 2>/dev/null || true
kubectl delete namespace $KYVERNO_NAMESPACE --ignore-not-found --wait=false

echo ""
echo "Kyverno removed."

# Optionally delete the cluster
echo ""
read -p "Delete the Minikube cluster '$CLUSTER_NAME'? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "Deleting cluster '$CLUSTER_NAME'..."
  minikube delete --profile $CLUSTER_NAME
  echo "Cluster deleted."
else
  echo "Cluster kept. To delete it later:"
  echo "  minikube delete --profile $CLUSTER_NAME"
fi

echo ""
echo "Cleanup complete."
