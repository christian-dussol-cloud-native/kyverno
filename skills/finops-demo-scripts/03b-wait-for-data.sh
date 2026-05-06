#!/bin/bash
# 03b-wait-for-data.sh
# Polls OpenCost API until allocation data is available, then exits.

set -e

PORT=9003
INTERVAL=30

echo "🔌 Starting port-forward to OpenCost on port $PORT..."
kubectl port-forward -n opencost svc/opencost $PORT:9003 &>/dev/null &
PF_PID=$!
trap "kill $PF_PID 2>/dev/null" EXIT

sleep 3

echo "⏳ Polling OpenCost allocation API every ${INTERVAL}s..."
echo "   (Ctrl+C to stop)"
echo ""

ATTEMPTS=0
while true; do
  ATTEMPTS=$((ATTEMPTS + 1))
  TIMESTAMP=$(date '+%H:%M:%S')

  RESPONSE=$(curl -sf "http://localhost:$PORT/allocation/compute?window=1h&aggregate=namespace" 2>/dev/null || echo "")

  if [ -z "$RESPONSE" ]; then
    echo "[$TIMESTAMP] attempt $ATTEMPTS — OpenCost not reachable yet"
  else
    # Check if any non-empty allocation data exists (not just __idle__)
    HAS_DATA=$(echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin).get('data', [{}])
    namespaces = [k for d in data for k in d.keys() if k not in ('__idle__', '__unmounted__')]
    print('yes' if namespaces else 'no')
    if namespaces:
        print('Namespaces with data: ' + ', '.join(namespaces), file=sys.stderr)
except:
    print('no')
" 2>/tmp/opencost_ns)

    NS_INFO=$(cat /tmp/opencost_ns 2>/dev/null || echo "")

    if [ "$HAS_DATA" = "yes" ]; then
      echo "[$TIMESTAMP] attempt $ATTEMPTS — ✅ Data available! $NS_INFO"
      echo ""
      echo "✅ OpenCost has allocation data. You can now run: ./04-connect-mcp.sh"
      exit 0
    else
      echo "[$TIMESTAMP] attempt $ATTEMPTS — collecting... (only __idle__ so far)"
    fi
  fi

  sleep $INTERVAL
done
