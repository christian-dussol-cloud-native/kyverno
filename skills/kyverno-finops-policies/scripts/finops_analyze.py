#!/usr/bin/env python3
"""
FinOps Policy Analyzer
Validates FinOps-specific parameters in generated Kyverno policies
and estimates cost impact.

Usage:
    python finops_analyze.py --file <policy.yaml>
    python finops_analyze.py --dir <policies/>
    python finops_analyze.py --file <policy.yaml> --format json

Checks:
    1. Tier consistency — are dev limits < staging < prod?
    2. Label completeness — are all required cost-allocation labels present?
    3. Threshold reasonableness — are CPU/memory caps realistic?
    4. Annotation format — FOCUS™ compliance check
    5. Cost impact estimate — rough monthly savings based on limit enforcement
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


# --- Constants ---

REQUIRED_COST_LABELS = [
    "team",
    "cost-center",
    "environment",
]

RECOMMENDED_COST_LABELS = [
    "service",
    "budget-owner",
    "project",
]

FOCUS_ANNOTATIONS = [
    "finops.kyverno.io/service-name",
    "finops.kyverno.io/charge-category",
    "finops.kyverno.io/resource-type",
]

# Reasonable thresholds for CPU (cores) and memory (Gi)
CPU_THRESHOLDS = {
    "min": 0.1,
    "max_dev": 4,
    "max_staging": 8,
    "max_prod": 16,
    "absolute_max": 64,
}

MEMORY_THRESHOLDS = {
    "min_gi": 0.064,  # 64Mi
    "max_dev_gi": 8,
    "max_staging_gi": 16,
    "max_prod_gi": 32,
    "absolute_max_gi": 128,
}

# Rough cost estimates ($/core/month, $/Gi/month) — cloud average
COST_PER_CORE_MONTH = 30.0
COST_PER_GI_MONTH = 4.0


# --- Data Classes ---

class CheckResult:
    """Result for a single check."""

    def __init__(self, name: str):
        self.name = name
        self.status = "pass"  # pass, warn, fail
        self.findings = []

    def fail(self, msg: str):
        self.status = "fail"
        self.findings.append(("error", msg))

    def warn(self, msg: str):
        if self.status != "fail":
            self.status = "warn"
        self.findings.append(("warning", msg))

    def ok(self, msg: str):
        self.findings.append(("ok", msg))

    @property
    def icon(self) -> str:
        return {"pass": "✅", "warn": "⚠️", "fail": "❌"}[self.status]

    @property
    def passed(self) -> bool:
        return self.status == "pass"


class FinOpsAnalysis:
    """Complete analysis result for a FinOps policy."""

    def __init__(self, file_path: str, policy_name: str):
        self.file_path = file_path
        self.policy_name = policy_name
        self.checks = {}
        self.parse_error = None
        self.savings_estimate = 0.0

    def add_check(self, check: CheckResult):
        self.checks[check.name] = check

    @property
    def score(self) -> int:
        return sum(1 for c in self.checks.values() if c.passed)

    @property
    def total(self) -> int:
        return len(self.checks)

    @property
    def score_label(self) -> str:
        return f"{self.score}/{self.total}"


# --- Parse Helpers ---

def _parse_cpu(value: str) -> float:
    """Parse CPU value to cores."""
    if not value or value in ("*", "?*"):
        return 0
    value = str(value).strip('"').strip("'")
    if value.endswith("m"):
        return float(value[:-1]) / 1000
    return float(value)


def _parse_memory_gi(value: str) -> float:
    """Parse memory value to Gi."""
    if not value or value in ("*", "?*"):
        return 0
    value = str(value).strip('"').strip("'")
    if value.endswith("Gi"):
        return float(value[:-2])
    if value.endswith("Mi"):
        return float(value[:-2]) / 1024
    if value.endswith("Ki"):
        return float(value[:-2]) / (1024 * 1024)
    return float(value) / (1024 * 1024 * 1024)


def _extract_limits(policy: dict) -> list:
    """Extract resource limits from policy rules."""
    limits = []
    rules = policy.get("spec", {}).get("rules", [])
    for rule in rules:
        rule_name = rule.get("name", "?")
        validate = rule.get("validate", {})
        pattern = validate.get("pattern", {})

        # Walk the pattern tree looking for resources.limits
        containers = (
            pattern.get("spec", {}).get("containers", [])
            or pattern.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        )
        if isinstance(containers, list):
            for container in containers:
                res = container.get("resources", {})
                lim = res.get("limits", {})
                req = res.get("requests", {})
                limits.append({
                    "rule": rule_name,
                    "cpu_limit": lim.get("cpu", ""),
                    "memory_limit": lim.get("memory", ""),
                    "cpu_request": req.get("cpu", ""),
                    "memory_request": req.get("memory", ""),
                })

        # Check foreach patterns too
        foreach = validate.get("foreach", [])
        if isinstance(foreach, list):
            for fe in foreach:
                deny = fe.get("deny", {})
                conditions = deny.get("conditions", {})
                if conditions:
                    limits.append({
                        "rule": rule_name,
                        "type": "foreach_deny",
                    })

    return limits


def _detect_environment_tier(rule_name: str, rule: dict) -> str:
    """Try to detect environment tier from rule name or match conditions."""
    name_lower = rule_name.lower()
    for tier in ["dev", "development", "staging", "stg", "prod", "production"]:
        if tier in name_lower:
            if "prod" in tier:
                return "prod"
            elif "stag" in tier or "stg" in tier:
                return "staging"
            else:
                return "dev"

    # Check match conditions for namespace selectors
    match = rule.get("match", {})
    match_str = json.dumps(match).lower()
    if "prod" in match_str:
        return "prod"
    elif "staging" in match_str or "stg" in match_str:
        return "staging"
    elif "dev" in match_str:
        return "dev"

    return "unknown"


# --- Checks ---

def check_tier_consistency(policy: dict) -> CheckResult:
    """Check 1: Are dev limits < staging < prod?"""
    check = CheckResult("Tier Consistency")
    rules = policy.get("spec", {}).get("rules", [])

    tiers = {}
    for rule in rules:
        rule_name = rule.get("name", "?")
        tier = _detect_environment_tier(rule_name, rule)
        if tier == "unknown":
            continue

        validate = rule.get("validate", {})
        pattern = validate.get("pattern", {})
        containers = (
            pattern.get("spec", {}).get("containers", [])
            or pattern.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
        )
        if isinstance(containers, list) and containers:
            for container in containers:
                cpu = container.get("resources", {}).get("limits", {}).get("cpu", "")
                mem = container.get("resources", {}).get("limits", {}).get("memory", "")
                tiers[tier] = {
                    "cpu": _parse_cpu(cpu),
                    "memory_gi": _parse_memory_gi(mem),
                    "rule": rule_name,
                }

    if not tiers:
        check.ok("No tiered rules detected — tier consistency check not applicable")
        return check

    if len(tiers) == 1:
        check.ok(f"Single tier detected: {list(tiers.keys())[0]}")
        return check

    # Check ordering
    tier_order = ["dev", "staging", "prod"]
    tier_values = [(t, tiers[t]) for t in tier_order if t in tiers]

    for i in range(len(tier_values) - 1):
        t1_name, t1 = tier_values[i]
        t2_name, t2 = tier_values[i + 1]

        if t1["cpu"] > 0 and t2["cpu"] > 0 and t1["cpu"] > t2["cpu"]:
            check.fail(
                f"CPU limit inconsistency: {t1_name} ({t1['cpu']} cores) > "
                f"{t2_name} ({t2['cpu']} cores)"
            )
        elif t1["cpu"] > 0 and t2["cpu"] > 0:
            check.ok(f"CPU: {t1_name} ({t1['cpu']}) <= {t2_name} ({t2['cpu']})")

        if t1["memory_gi"] > 0 and t2["memory_gi"] > 0 and t1["memory_gi"] > t2["memory_gi"]:
            check.fail(
                f"Memory limit inconsistency: {t1_name} ({t1['memory_gi']}Gi) > "
                f"{t2_name} ({t2['memory_gi']}Gi)"
            )
        elif t1["memory_gi"] > 0 and t2["memory_gi"] > 0:
            check.ok(f"Memory: {t1_name} ({t1['memory_gi']}Gi) <= {t2_name} ({t2['memory_gi']}Gi)")

    return check


def check_label_completeness(policy: dict) -> CheckResult:
    """Check 2: Are all required cost-allocation labels enforced?"""
    check = CheckResult("Label Completeness")
    rules = policy.get("spec", {}).get("rules", [])

    # Collect all label keys referenced in the policy
    policy_text = json.dumps(policy).lower()

    found_required = []
    missing_required = []
    for label in REQUIRED_COST_LABELS:
        if label.lower() in policy_text:
            found_required.append(label)
        else:
            missing_required.append(label)

    found_recommended = []
    missing_recommended = []
    for label in RECOMMENDED_COST_LABELS:
        if label.lower() in policy_text:
            found_recommended.append(label)
        else:
            missing_recommended.append(label)

    if missing_required:
        check.warn(f"Missing required cost labels: {', '.join(missing_required)}")
    else:
        check.ok(f"All required cost labels present: {', '.join(found_required)}")

    if missing_recommended:
        check.ok(f"Optional labels not enforced: {', '.join(missing_recommended)}")

    if found_recommended:
        check.ok(f"Recommended labels also enforced: {', '.join(found_recommended)}")

    return check


def check_threshold_reasonableness(policy: dict) -> CheckResult:
    """Check 3: Are CPU/memory caps realistic?"""
    check = CheckResult("Threshold Reasonableness")
    limits = _extract_limits(policy)

    if not limits:
        check.ok("No explicit resource thresholds found — check not applicable")
        return check

    for lim in limits:
        rule = lim.get("rule", "?")

        cpu = lim.get("cpu_limit", "")
        if cpu and cpu not in ("*", "?*"):
            cpu_val = _parse_cpu(cpu)
            if cpu_val > 0:
                if cpu_val < CPU_THRESHOLDS["min"]:
                    check.warn(f"Rule '{rule}': CPU limit {cpu_val} cores is very low (<{CPU_THRESHOLDS['min']})")
                elif cpu_val > CPU_THRESHOLDS["absolute_max"]:
                    check.fail(f"Rule '{rule}': CPU limit {cpu_val} cores is unreasonably high (>{CPU_THRESHOLDS['absolute_max']})")
                else:
                    check.ok(f"Rule '{rule}': CPU limit {cpu_val} cores — reasonable")

        mem = lim.get("memory_limit", "")
        if mem and mem not in ("*", "?*"):
            mem_val = _parse_memory_gi(mem)
            if mem_val > 0:
                if mem_val < MEMORY_THRESHOLDS["min_gi"]:
                    check.warn(f"Rule '{rule}': Memory limit {mem_val}Gi is very low (<{MEMORY_THRESHOLDS['min_gi']}Gi)")
                elif mem_val > MEMORY_THRESHOLDS["absolute_max_gi"]:
                    check.fail(f"Rule '{rule}': Memory limit {mem_val}Gi is unreasonably high (>{MEMORY_THRESHOLDS['absolute_max_gi']}Gi)")
                else:
                    check.ok(f"Rule '{rule}': Memory limit {mem_val}Gi — reasonable")

    return check


def check_focus_compliance(policy: dict) -> CheckResult:
    """Check 4: FOCUS™ annotation format compliance."""
    check = CheckResult("FOCUS™ Compliance")
    annotations = policy.get("metadata", {}).get("annotations", {})

    if not annotations:
        check.warn("No annotations — cannot check FOCUS™ compliance")
        return check

    found = []
    missing = []
    for ann in FOCUS_ANNOTATIONS:
        if ann in annotations:
            found.append(ann)
        else:
            missing.append(ann)

    if missing:
        check.warn(f"Missing FOCUS™ annotations: {', '.join(missing)}")
    else:
        check.ok("All FOCUS™ annotations present")

    # Check that category is FinOps
    category = annotations.get("policies.kyverno.io/category", "")
    if category and "finops" in category.lower():
        check.ok(f"Category: {category}")
    elif category:
        check.warn(f"Category is '{category}' — expected 'FinOps' for cost governance policies")
    else:
        check.warn("Missing policies.kyverno.io/category annotation")

    return check


def check_cost_estimate(policy: dict) -> tuple:
    """Check 5: Rough monthly savings estimate."""
    check = CheckResult("Cost Estimate")
    savings = 0.0

    limits = _extract_limits(policy)
    if not limits:
        check.ok("No explicit limits — cannot estimate savings")
        return check, 0.0

    for lim in limits:
        cpu = lim.get("cpu_limit", "")
        if cpu and cpu not in ("*", "?*"):
            cpu_val = _parse_cpu(cpu)
            if cpu_val > 0:
                # Estimate: average pod wastes ~40% of requested CPU
                estimated_savings_per_pod = cpu_val * 0.4 * COST_PER_CORE_MONTH
                savings += estimated_savings_per_pod

        mem = lim.get("memory_limit", "")
        if mem and mem not in ("*", "?*"):
            mem_val = _parse_memory_gi(mem)
            if mem_val > 0:
                estimated_savings_per_pod = mem_val * 0.3 * COST_PER_GI_MONTH
                savings += estimated_savings_per_pod

    if savings > 0:
        check.ok(f"Estimated savings: ~${savings:.0f}/pod/month (based on average waste reduction)")
    else:
        check.ok("No quantifiable savings estimate available")

    return check, savings


# --- Main Analysis ---

def analyze_policy(file_path: str) -> FinOpsAnalysis:
    """Analyze a single FinOps policy."""
    path = Path(file_path)
    content = path.read_text()

    try:
        docs = list(yaml.safe_load_all(content))
        policy = docs[0] if docs else None
    except yaml.YAMLError as e:
        analysis = FinOpsAnalysis(file_path, "PARSE_ERROR")
        analysis.parse_error = str(e)
        return analysis

    if not policy or not isinstance(policy, dict):
        analysis = FinOpsAnalysis(file_path, "EMPTY")
        analysis.parse_error = "Empty or invalid YAML"
        return analysis

    policy_name = policy.get("metadata", {}).get("name", Path(file_path).stem)
    analysis = FinOpsAnalysis(file_path, policy_name)

    # Run all 5 checks
    analysis.add_check(check_tier_consistency(policy))
    analysis.add_check(check_label_completeness(policy))
    analysis.add_check(check_threshold_reasonableness(policy))
    analysis.add_check(check_focus_compliance(policy))

    cost_check, savings = check_cost_estimate(policy)
    analysis.add_check(cost_check)
    analysis.savings_estimate = savings

    return analysis


# --- Output Formatters ---

def format_text(analysis: FinOpsAnalysis) -> str:
    """Format analysis as text."""
    lines = []
    lines.append(f"\n💰 FinOps Policy Analyzer")
    lines.append(f"{'=' * 50}")
    lines.append(f"📄 Policy: {analysis.policy_name}")
    lines.append(f"📁 File: {analysis.file_path}")

    if analysis.parse_error:
        lines.append(f"\n❌ Parse error: {analysis.parse_error}")
        return "\n".join(lines)

    lines.append(f"📊 Score: {analysis.score_label}")
    lines.append("")

    for check in analysis.checks.values():
        lines.append(f"  {check.icon} {check.name}")
        for level, msg in check.findings:
            if level == "error":
                lines.append(f"      ❌ {msg}")
            elif level == "warning":
                lines.append(f"      ⚠️  {msg}")

    if analysis.savings_estimate > 0:
        lines.append(f"\n💰 Estimated savings: ~${analysis.savings_estimate:.0f}/pod/month")

    lines.append("")
    if all(c.passed for c in analysis.checks.values()):
        lines.append("✅ FinOps policy meets all governance criteria.")
    else:
        lines.append("⚠️  Review findings above — some criteria need attention.")

    return "\n".join(lines)


def format_json(analysis: FinOpsAnalysis) -> str:
    """Format analysis as JSON."""
    output = {
        "file": analysis.file_path,
        "policy": analysis.policy_name,
        "score": analysis.score,
        "total": analysis.total,
        "savings_estimate": analysis.savings_estimate,
    }
    if analysis.parse_error:
        output["parse_error"] = analysis.parse_error
    else:
        output["checks"] = {}
        for check in analysis.checks.values():
            output["checks"][check.name] = {
                "status": check.status,
                "findings": [
                    {"level": level, "message": msg}
                    for level, msg in check.findings
                ],
            }
    return json.dumps(output, indent=2)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Analyze FinOps Kyverno policies")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single policy YAML file")
    group.add_argument("--dir", help="Path to a directory of policy YAML files")
    parser.add_argument("--format", choices=["text", "json"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        analysis = analyze_policy(args.file)
        analyses = [analysis]
    else:
        path = Path(args.dir)
        if not path.is_dir():
            print(f"❌ Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        analyses = []
        for yaml_file in sorted(list(path.glob("**/*.yaml")) + list(path.glob("**/*.yml"))):
            if yaml_file.name.startswith("test-") or "chainsaw" in yaml_file.name.lower():
                continue
            analysis = analyze_policy(str(yaml_file))
            if analysis:
                analyses.append(analysis)

    if args.format == "json":
        print(json.dumps([json.loads(format_json(a)) for a in analyses], indent=2))
    else:
        for analysis in analyses:
            print(format_text(analysis))

    all_passed = all(
        all(c.passed for c in a.checks.values())
        for a in analyses if not a.parse_error
    )
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
