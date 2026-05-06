# Demo Scripts

Scripts to set up and tear down the FinOps demo environment.

## Prerequisites

- `minikube` installed
- `kubectl` configured
- `helm` installed
- `python3` installed
- `claude` CLI installed (Claude Code)
- Kyverno **v1.10+** already installed on the cluster (tested on v1.15.2)

## Run the demo

Execute the scripts in order:

```bash
cd finops-demo-scripts/
chmod u+x *.sh

./01-start-minikube.sh         # Start Minikube with 4Gi memory, 2 CPUs
./02-install-opencost.sh       # Install Prometheus + OpenCost
./03-deploy-demo-workloads.sh  # Deploy waste-test pod (dev) + prod-test pod (prod)
./03b-wait-for-data.sh         # Poll OpenCost API — exits when data is ready
./04-connect-mcp.sh            # Port-forward + connect to Claude Code
```

Then in a new terminal:

```bash
claude
> "Analyze my cluster costs and suggest governance policies"
```

## Tear down

When done with the demo:

```bash
./05-cleanup.sh                # Remove resources, optionally stop Minikube
```

## What each script does

| Script | Purpose | Runtime |
|--------|---------|---------|
| 01-start-minikube.sh | Start Minikube with adequate resources | ~1 min |
| 02-install-opencost.sh | Helm install Prometheus (prometheus-system) + OpenCost (opencost) | ~4 min |
| 03-deploy-demo-workloads.sh | Create dev-team-a + prod-payments namespaces with sample pods | ~30 sec |
| 03b-wait-for-data.sh | Poll OpenCost API every 30s, exit when allocation data is available | ~15-20 min |
| 04-connect-mcp.sh | Port-forward OpenCost on 8081, register with Claude Code | ~5 sec |
| 05-cleanup.sh | Uninstall OpenCost + Prometheus, delete demo namespaces, stop Minikube | ~1 min |

## Notes

- Script 04 starts a port-forward in the background. Keep that terminal open while using the Skill.
- Total setup time: ~5 minutes + 15-20 minutes for OpenCost data collection (monitored by 03b).
- These scripts are for educational purposes, demonstrating the FinOps Skill setup.
