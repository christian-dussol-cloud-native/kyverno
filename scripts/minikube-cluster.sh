#!/bin/bash
set -e

# =============================================================================
# Minikube Cluster — Kyverno Lab
# =============================================================================
# Creates a local Minikube cluster ready for Kyverno policy testing.
# =============================================================================

CLUSTER_NAME="kyverno-lab"
DRIVER="docker"       # Change to 'virtualbox' or 'podman' if needed
KUBERNETES_VERSION="1.30.0"
CPUS="2"
MEMORY="4096"
NODES="1"

echo "Creating Minikube cluster for Kyverno..."

# Check if Minikube is installed
if ! command -v minikube &> /dev/null; then
  echo "Minikube not found. Install from: https://minikube.sigs.k8s.io/docs/start/"
  exit 1
fi

# Check if cluster already exists
if minikube status -p $CLUSTER_NAME &> /dev/null; then
  echo "Cluster '$CLUSTER_NAME' already exists."
  read -p "Delete and recreate? (y/n): " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Deleting existing cluster..."
    minikube delete -p $CLUSTER_NAME
  else
    echo "Using existing cluster."
    exit 0
  fi
fi

# Create cluster
echo "Creating Minikube cluster (this may take 2-3 minutes)..."
minikube start \
  --profile=$CLUSTER_NAME \
  --driver=$DRIVER \
  --kubernetes-version=$KUBERNETES_VERSION \
  --cpus=$CPUS \
  --memory=$MEMORY \
  --nodes=$NODES

# Verify cluster
echo ""
echo "Cluster created successfully!"
kubectl get nodes

echo ""
echo "Next step:"
echo "  ./scripts/install-kyverno.sh"
