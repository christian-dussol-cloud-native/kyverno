#!/bin/bash
# 04-connect-mcp.sh
# Port-forwards OpenCost MCP server and connects it to Claude Code.
#
# IMPORTANT: This script starts a port-forward in the background.
# Keep this terminal open while using the FinOps Skill in Claude Code.

set -e

echo "🔌 Starting port-forward for OpenCost MCP server (port 8081)..."
# Kill any existing port-forward on 8081
pkill -f "port-forward.*8081" 2>/dev/null && sleep 1 || true

kubectl port-forward -n opencost svc/opencost 8081:8081 &
PORT_FORWARD_PID=$!

# Give port-forward time to establish and check it didn't fail
sleep 3
if ! kill -0 $PORT_FORWARD_PID 2>/dev/null; then
  echo "❌ Port-forward failed to start. Check: kubectl get pods -n opencost"
  exit 1
fi

echo ""
echo "🔍 Verifying MCP endpoint..."
if nc -z localhost 8081 2>/dev/null; then
  echo "✅ OpenCost MCP listening on port 8081"
else
  echo "⚠️  Port 8081 not reachable yet. Check: kubectl get pods -n opencost"
fi

echo ""
echo "🔗 Adding OpenCost MCP to Claude Code..."
claude mcp remove opencost 2>/dev/null || true
claude mcp add opencost --transport http http://localhost:8081

echo ""
echo "📋 Verifying MCP registration..."
claude mcp list

echo ""
echo "✅ Setup complete."
echo ""
echo "Port-forward PID: $PORT_FORWARD_PID (keep this terminal open)"
echo ""
echo "To test the FinOps Skill, open a new terminal and run:"
echo "  claude"
echo "  > \"Analyze my cluster costs and suggest governance policies\""
echo ""
echo "When done, run: ./05-cleanup.sh"
