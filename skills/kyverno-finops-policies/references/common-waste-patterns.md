# Common Waste Patterns

The most frequent sources of Kubernetes cost waste, ranked by financial impact.

## 1. Over-Provisioned CPU Requests (40-60% of waste)

**What happens:** Teams set CPU requests based on peak usage or copy-paste
from examples. In practice, most pods use 10-30% of requested CPU.

**Example:** Pod requests 4 cores, consistently uses 0.8 cores. 80% waste.

**Policy fix:** Tiered limits by environment + over-provisioning guard
requiring justification above 4 cores.

## 2. Missing Resource Limits (20-30% of waste)

**What happens:** Pods without limits can consume all available node resources.
One runaway pod can impact every other pod on the node.

**Example:** A dev pod with no limits consumes 12 cores during a load test,
starving 8 other pods on the same node.

**Policy fix:** Require memory limits on all pods (CPU limits optional
per Burstable QoS best practice).

## 3. Orphaned Resources (10-15% of waste)

**What happens:** PVCs, LoadBalancers, and ConfigMaps left behind after
deployments are deleted. They continue to incur costs.

**Example:** 40 unattached PVCs across dev namespaces, each costing $5/month.
$200/month in invisible waste.

**Policy fix:** Require owner labels on all persistent resources.
Generate cleanup policies for resources without recent activity.

## 4. Missing Cost-Allocation Labels (indirect waste)

**What happens:** Without team/cost-center labels, costs can't be attributed.
Teams don't optimize what they can't see.

**Example:** 30% of namespaces have no cost-center label. Finance team
can't allocate $15,000/month of cloud spend to any business unit.

**Policy fix:** Require team, cost-center, and environment labels on all pods.

## 5. Dev/Test Running 24/7 (5-10% of waste)

**What happens:** Development and test environments run continuously,
even though they're only used during business hours.

**Example:** Dev cluster runs 16 hours/day idle. 67% waste on compute.

**Policy fix:** While Kyverno can't schedule downtime directly,
it can enforce annotations that downstream tools (Keda, CronJobs)
use to implement scaling schedules.
