#!/bin/bash
# 01-start-minikube.sh
# Starts Minikube with adequate resources for OpenCost + sample workloads.

set -e

echo "🚀 Starting Minikube with 4Gi memory and 2 CPUs..."
minikube start --memory 4096 --cpus 2

echo ""
echo "✅ Minikube ready."
echo ""
echo "Verify with: kubectl get nodes"
kubectl get nodes

echo ""
echo "Next step: ./02-install-opencost.sh"
