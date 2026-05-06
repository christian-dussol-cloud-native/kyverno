#!/bin/bash
# 05-cleanup.sh
# Cleans up demo resources and stops Minikube.

set +e  # Don't fail if some resources don't exist

echo "🧹 Removing OpenCost MCP from Claude Code..."
claude mcp remove opencost 2>/dev/null || echo "  opencost MCP already removed or not found"

echo ""
echo "🧹 Stopping any port-forward processes..."
pkill -f "port-forward.*8081" 2>/dev/null || true
pkill -f "port-forward.*9003" 2>/dev/null || true
pkill -f "port-forward.*9090" 2>/dev/null || true
echo "  port-forwards stopped"

echo ""
echo "🧹 Deleting demo workloads and namespaces..."
kubectl delete namespace dev-team-a --ignore-not-found=true
kubectl delete namespace prod-payments --ignore-not-found=true

echo ""
echo "🧹 Uninstalling OpenCost..."
helm uninstall opencost -n opencost 2>/dev/null || echo "  opencost not installed"
kubectl delete namespace opencost --ignore-not-found=true

echo ""
echo "🧹 Uninstalling Prometheus..."
helm uninstall prometheus -n prometheus-system 2>/dev/null || echo "  prometheus not installed"
kubectl delete namespace prometheus-system --ignore-not-found=true

echo ""
read -p "Stop Minikube? (y/N) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
  echo "🛑 Stopping Minikube..."
  minikube stop
  echo "✅ Minikube stopped."
else
  echo "✅ Demo resources cleaned. Minikube still running."
fi

echo ""
echo "Cleanup complete."
