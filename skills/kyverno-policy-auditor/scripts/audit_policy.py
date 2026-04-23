#!/usr/bin/env python3
"""
Kyverno Policy Auditor
Audits existing Kyverno policies against best practices and production standards.

Usage:
    python audit_policy.py --file <policy.yaml>
    python audit_policy.py --dir <policies/>
    python audit_policy.py --dir <policies/> --strict --format json

Audit dimensions:
    1. Structure       — apiVersion, kind, name, rules
    2. Annotations     — title, category, severity, description
    3. Labels          — managed-by, governance tracking
    4. Safe Defaults   — Audit mode, background scan
    5. Autogen         — targets Pod, match.any wrapper
    6. Pattern Quality — "?*" patterns, valid operators
    7. Message Quality — actionable, specific, >20 chars
    8. Test Coverage   — Chainsaw test, pass/block resources
"""

import argparse
import json
import os
import sys
from pathlib import Path

import yaml


# --- Constants ---

REQUIRED_ANNOTATIONS = [
    "policies.kyverno.io/title",
    "policies.kyverno.io/category",
    "policies.kyverno.io/severity",
    "policies.kyverno.io/description",
]

RECOMMENDED_ANNOTATIONS = [
    "policies.kyverno.io/subject",
    "policies.kyverno.io/minversion",
]

VALID_SEVERITIES = ["low", "medium", "high", "critical"]
VALID_ACTIONS = ["Audit", "Enforce", "audit", "enforce"]
VALID_RULE_TYPES = ["validate", "mutate", "generate", "verifyImages"]
VALID_OPERATORS = {
    "Equals", "NotEquals", "Equal", "NotEqual",
    "In", "NotIn", "AnyIn", "AnyNotIn", "AllIn", "AllNotIn",
    "GreaterThan", "GreaterThanOrEquals",
    "LessThan", "LessThanOrEquals",
    "DurationGreaterThan", "DurationGreaterThanOrEquals",
    "DurationLessThan", "DurationLessThanOrEquals",
}

MUTATE_RULE_TYPES = {"mutate", "verifyImages"}


# --- Data Classes ---

class DimensionResult:
    """Result for a single audit dimension."""

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


class PolicyAudit:
    """Complete audit result for a single policy."""

    def __init__(self, file_path: str, policy_name: str):
        self.file_path = file_path
        self.policy_name = policy_name
        self.dimensions = {}
        self.parse_error = None

    def add_dimension(self, dim: DimensionResult):
        self.dimensions[dim.name] = dim

    @property
    def score(self) -> int:
        return sum(1 for d in self.dimensions.values() if d.passed)

    @property
    def total(self) -> int:
        return len(self.dimensions)

    @property
    def score_label(self) -> str:
        return f"{self.score}/{self.total}"

    @property
    def passed(self) -> bool:
        return all(d.passed for d in self.dimensions.values())

    def critical_issues(self) -> list:
        issues = []
        for d in self.dimensions.values():
            if d.status == "fail":
                for level, msg in d.findings:
                    if level == "error":
                        issues.append(msg)
        return issues


# --- Audit Dimensions ---

def audit_structure(policy: dict) -> DimensionResult:
    """Dimension 1: Structure."""
    dim = DimensionResult("Structure")

    api = policy.get("apiVersion", "")
    if api in ("kyverno.io/v1", "kyverno.io/v2beta1"):
        dim.ok(f"Valid apiVersion: {api}")
    else:
        dim.fail(f"Invalid apiVersion: '{api}'")

    kind = policy.get("kind", "")
    if kind in ("ClusterPolicy", "Policy"):
        dim.ok(f"Valid kind: {kind}")
    else:
        dim.fail(f"Invalid kind: '{kind}'")

    name = policy.get("metadata", {}).get("name", "")
    if name:
        dim.ok(f"Policy name: {name}")
        if "_" in name:
            dim.warn("Name uses underscores — dashes are preferred")
    else:
        dim.fail("Missing metadata.name")

    rules = policy.get("spec", {}).get("rules", [])
    if rules:
        dim.ok(f"Rules defined: {len(rules)}")
    else:
        dim.fail("No rules in spec.rules")

    return dim


def audit_annotations(policy: dict, strict: bool = False) -> DimensionResult:
    """Dimension 2: Annotations."""
    dim = DimensionResult("Annotations")
    annotations = policy.get("metadata", {}).get("annotations", {})

    if not annotations:
        dim.fail("No annotations defined")
        return dim

    missing = []
    for ann in REQUIRED_ANNOTATIONS:
        value = annotations.get(ann, "")
        if value:
            dim.ok(f"Present: {ann}")
        else:
            missing.append(ann)

    if missing:
        if strict:
            dim.fail(f"Missing required: {', '.join(missing)}")
        else:
            dim.warn(f"Missing: {', '.join(missing)}")
    else:
        dim.ok("All required annotations present")

    severity = annotations.get("policies.kyverno.io/severity", "")
    if severity and severity not in VALID_SEVERITIES:
        dim.warn(f"Non-standard severity: '{severity}'")

    description = annotations.get("policies.kyverno.io/description", "")
    if description and len(description) < 20:
        dim.warn("Description is very short (<20 chars)")

    return dim


def audit_labels(policy: dict) -> DimensionResult:
    """Dimension 3: Labels."""
    dim = DimensionResult("Labels")
    labels = policy.get("metadata", {}).get("labels", {})

    if not labels:
        dim.warn("No labels defined")
        return dim

    managed_by = labels.get("app.kubernetes.io/managed-by", "")
    if managed_by:
        dim.ok(f"managed-by: {managed_by}")
    else:
        dim.warn("Missing app.kubernetes.io/managed-by label")

    # Check for any governance-related labels
    governance_keys = [k for k in labels if "kyverno" in k.lower() or "governance" in k.lower()]
    if governance_keys:
        dim.ok(f"Governance labels: {', '.join(governance_keys)}")
    else:
        dim.warn("No governance tracking labels found")

    return dim


def audit_safe_defaults(policy: dict) -> DimensionResult:
    """Dimension 4: Safe Defaults."""
    dim = DimensionResult("Safe Defaults")
    spec = policy.get("spec", {})
    rules = spec.get("rules", [])

    # Check validationFailureAction
    action = spec.get("validationFailureAction", "")
    if not action:
        dim.warn("validationFailureAction not set (defaults vary by Kyverno version)")
    elif action.lower() == "audit":
        dim.ok("Audit mode (safe-first)")
    elif action.lower() == "enforce":
        dim.warn("Enforce mode — ensure this is intentional and tested")
    else:
        dim.fail(f"Invalid validationFailureAction: '{action}'")

    # Check background based on rule types
    background = spec.get("background")
    rule_types = set()
    for rule in rules:
        for rt in VALID_RULE_TYPES:
            if rt in rule:
                rule_types.add(rt)

    if rule_types & MUTATE_RULE_TYPES:
        # Mutate/verifyImages should have background: false
        if background is False:
            dim.ok("background: false (correct for mutate/verifyImages)")
        elif background is True:
            dim.warn("background: true on mutate/verifyImages — mutations only apply at admission")
        # background not set is acceptable
    else:
        # Validate/generate should have background: true
        if background is True:
            dim.ok("background: true (scans existing resources)")
        elif background is False:
            dim.warn("background: false on validate policy — existing resources won't be scanned")
        else:
            dim.warn("background not set — consider background: true to scan existing resources")

    return dim


def audit_autogen(policy: dict) -> DimensionResult:
    """Dimension 5: Autogen Compatibility."""
    dim = DimensionResult("Autogen")
    rules = policy.get("spec", {}).get("rules", [])

    for rule in rules:
        rule_name = rule.get("name", "?")
        match = rule.get("match", {})

        # Check match.any wrapper
        if "any" in match:
            dim.ok(f"Rule '{rule_name}': uses match.any (canonical)")
            any_list = match["any"]
            if any_list:
                kinds = any_list[0].get("resources", {}).get("kinds", [])
                if "Pod" in kinds:
                    dim.ok(f"Rule '{rule_name}': targets Pod (autogen compatible)")
                elif kinds:
                    workload_kinds = {"Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob"}
                    targeted_workloads = set(kinds) & workload_kinds
                    if targeted_workloads:
                        dim.warn(
                            f"Rule '{rule_name}': targets {', '.join(kinds)} directly. "
                            f"Consider targeting Pod for autogen to cover all workload types."
                        )
                    else:
                        dim.ok(f"Rule '{rule_name}': targets {', '.join(kinds)}")
        elif "resources" in match:
            dim.warn(f"Rule '{rule_name}': uses match.resources without any: wrapper")
            kinds = match.get("resources", {}).get("kinds", [])
            if kinds:
                dim.ok(f"Rule '{rule_name}': targets {', '.join(kinds)}")
        else:
            dim.warn(f"Rule '{rule_name}': unusual match structure")

    if not rules:
        dim.fail("No rules to check autogen compatibility")

    return dim


def _find_patterns(obj, path: str, findings: list):
    """Recursively find pattern values like '*' vs '?*'."""
    if isinstance(obj, str):
        if obj == "*":
            findings.append(("warn", path, "Uses '*' — allows empty values. Use '?*' for non-empty."))
        elif obj == "?*":
            findings.append(("ok", path, "Uses '?*' (non-empty required)"))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _find_patterns(v, f"{path}.{k}", findings)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _find_patterns(v, f"{path}[{i}]", findings)


def _collect_operators(obj, operators: list):
    """Recursively collect all operator values."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "operator" and isinstance(v, str):
                operators.append(v)
            else:
                _collect_operators(v, operators)
    elif isinstance(obj, list):
        for item in obj:
            _collect_operators(item, operators)


def audit_pattern_quality(policy: dict) -> DimensionResult:
    """Dimension 6: Pattern Quality."""
    dim = DimensionResult("Pattern Quality")
    rules = policy.get("spec", {}).get("rules", [])

    # Check pattern values
    pattern_findings = []
    for rule in rules:
        rule_name = rule.get("name", "?")
        validate = rule.get("validate", {})
        pattern = validate.get("pattern", {})
        if pattern:
            _find_patterns(pattern, f"rule '{rule_name}'", pattern_findings)

    star_count = sum(1 for level, _, _ in pattern_findings if level == "warn")
    qstar_count = sum(1 for level, _, _ in pattern_findings if level == "ok")

    if star_count > 0:
        dim.warn(f"{star_count} field(s) use '*' instead of '?*' — allows empty values")
        for level, path, msg in pattern_findings:
            if level == "warn":
                dim.warn(f"  {path}: {msg}")
    if qstar_count > 0:
        dim.ok(f"{qstar_count} field(s) correctly use '?*'")

    # Check operators
    operators_found = []
    for rule in rules:
        _collect_operators(rule, operators_found)

    invalid_ops = [op for op in operators_found if op not in VALID_OPERATORS]
    if invalid_ops:
        dim.fail(f"Invalid operators: {', '.join(set(invalid_ops))}")
    elif operators_found:
        dim.ok(f"All {len(operators_found)} operator(s) are valid")

    # Check for common LLM hallucination: forEach variable outside forEach
    for rule in rules:
        rule_name = rule.get("name", "?")
        validate = rule.get("validate", {})
        message = validate.get("message", "")
        has_foreach = "foreach" in validate
        if has_foreach and "element." in message:
            dim.warn(
                f"Rule '{rule_name}': message references 'element.*' "
                f"but message is outside foreach scope"
            )

    if not pattern_findings and not operators_found:
        dim.ok("No patterns or operators to check")

    return dim


def audit_message_quality(policy: dict) -> DimensionResult:
    """Dimension 7: Message Quality."""
    dim = DimensionResult("Message Quality")
    rules = policy.get("spec", {}).get("rules", [])

    for rule in rules:
        rule_name = rule.get("name", "?")
        rule_type = None
        for rt in VALID_RULE_TYPES:
            if rt in rule:
                rule_type = rt
                break

        if rule_type == "validate":
            validate = rule.get("validate", {})
            message = validate.get("message", "")

            if not message:
                dim.warn(f"Rule '{rule_name}': no validate.message defined")
            elif len(message) < 20:
                dim.warn(f"Rule '{rule_name}': message is very short ({len(message)} chars) — make it actionable")
            elif any(keyword in message.lower() for keyword in ["required", "must", "not allowed", "invalid"]):
                dim.ok(f"Rule '{rule_name}': message is actionable ({len(message)} chars)")
            else:
                dim.ok(f"Rule '{rule_name}': message present ({len(message)} chars)")

    validate_rules = [r for r in rules if "validate" in r]
    if not validate_rules:
        dim.ok("No validate rules — message check not applicable")

    return dim


def audit_test_coverage(policy: dict, file_path: str) -> DimensionResult:
    """Dimension 8: Test Coverage."""
    dim = DimensionResult("Test Coverage")
    policy_dir = Path(file_path).parent

    # Look for Chainsaw test file
    chainsaw_patterns = [
        "chainsaw-test.yaml", "chainsaw-test.yml",
        "test.yaml", "test.yml",
    ]
    policy_name = policy.get("metadata", {}).get("name", "")
    if policy_name:
        chainsaw_patterns.extend([
            f"test-{policy_name}.yaml",
            f"test-{policy_name}.yml",
        ])

    found_test = False
    for pattern in chainsaw_patterns:
        if (policy_dir / pattern).exists():
            dim.ok(f"Chainsaw test found: {pattern}")
            found_test = True
            break

    if not found_test:
        dim.warn(
            "No Chainsaw test found alongside policy. "
            "Consider using kyverno-policy-generator to create tests."
        )

    # Look for test resources
    found_pass = any(
        (policy_dir / f).exists()
        for f in ["test-pass.yaml", "test-pass.yml"]
    )
    found_block = any(
        (policy_dir / f).exists()
        for f in ["test-block.yaml", "test-block.yml"]
    )

    if found_pass and found_block:
        dim.ok("Test resources found (pass + block)")
    elif found_pass or found_block:
        dim.warn("Partial test resources — need both test-pass and test-block")
    elif found_test:
        dim.warn("Chainsaw test exists but no test-pass/test-block resources found")

    if not found_test and not found_pass and not found_block:
        dim.fail("No test coverage — policy is untested")

    return dim


# --- Main Audit Pipeline ---

def audit_single_policy(file_path: str, strict: bool = False) -> PolicyAudit:
    """Audit a single Kyverno policy file."""
    path = Path(file_path)
    content = path.read_text()

    try:
        docs = list(yaml.safe_load_all(content))
        policy = docs[0] if docs else None
    except yaml.YAMLError as e:
        audit = PolicyAudit(file_path, "PARSE_ERROR")
        audit.parse_error = str(e)
        return audit

    if not policy or not isinstance(policy, dict):
        audit = PolicyAudit(file_path, "EMPTY")
        audit.parse_error = "Empty or invalid YAML"
        return audit

    # Skip non-Kyverno resources
    api = policy.get("apiVersion", "")
    if "kyverno" not in api:
        return None  # Not a Kyverno policy

    policy_name = policy.get("metadata", {}).get("name", Path(file_path).stem)
    audit = PolicyAudit(file_path, policy_name)

    # Run all 8 dimensions
    audit.add_dimension(audit_structure(policy))
    audit.add_dimension(audit_annotations(policy, strict))
    audit.add_dimension(audit_labels(policy))
    audit.add_dimension(audit_safe_defaults(policy))
    audit.add_dimension(audit_autogen(policy))
    audit.add_dimension(audit_pattern_quality(policy))
    audit.add_dimension(audit_message_quality(policy))
    audit.add_dimension(audit_test_coverage(policy, file_path))

    return audit


def audit_directory(dir_path: str, strict: bool = False) -> list:
    """Audit all Kyverno policies in a directory."""
    results = []
    path = Path(dir_path)

    yaml_files = sorted(list(path.glob("**/*.yaml")) + list(path.glob("**/*.yml")))

    for yaml_file in yaml_files:
        # Skip test files and chainsaw files
        name = yaml_file.name.lower()
        if name.startswith("test-") or "chainsaw" in name:
            continue

        audit = audit_single_policy(str(yaml_file), strict)
        if audit is not None:  # Skip non-Kyverno files
            results.append(audit)

    return results


# --- Output Formatters ---

def format_single_text(audit: PolicyAudit) -> str:
    """Format a single policy audit as text."""
    lines = []
    lines.append(f"\n🔍 Kyverno Policy Auditor")
    lines.append(f"{'=' * 50}")
    lines.append(f"📄 Policy: {audit.policy_name}")
    lines.append(f"📁 File: {audit.file_path}")

    if audit.parse_error:
        lines.append(f"\n❌ Parse error: {audit.parse_error}")
        return "\n".join(lines)

    lines.append(f"📊 Score: {audit.score_label}")
    lines.append("")

    for dim in audit.dimensions.values():
        lines.append(f"  {dim.icon} {dim.name}")
        for level, msg in dim.findings:
            if level == "error":
                lines.append(f"      ❌ {msg}")
            elif level == "warning":
                lines.append(f"      ⚠️  {msg}")

    lines.append("")
    if audit.passed:
        lines.append("✅ Policy meets all audit criteria.")
    else:
        critical = audit.critical_issues()
        if critical:
            lines.append(f"❌ {len(critical)} critical issue(s) to fix.")
        else:
            lines.append("⚠️  Policy has warnings — review recommended.")

    return "\n".join(lines)


def format_batch_text(audits: list) -> str:
    """Format multiple policy audits as a summary report."""
    lines = []
    lines.append(f"\n🔍 Kyverno Policy Auditor — Batch Report")
    lines.append(f"{'=' * 50}")
    lines.append(f"📊 Policies audited: {len(audits)}")

    if not audits:
        lines.append("No Kyverno policies found.")
        return "\n".join(lines)

    # Parse errors
    parse_errors = [a for a in audits if a.parse_error]
    valid_audits = [a for a in audits if not a.parse_error]

    if parse_errors:
        lines.append(f"⚠️  Parse errors: {len(parse_errors)}")
        for a in parse_errors:
            lines.append(f"    {a.file_path}: {a.parse_error}")

    if not valid_audits:
        return "\n".join(lines)

    # Overall score
    total_score = sum(a.score for a in valid_audits)
    total_possible = sum(a.total for a in valid_audits)
    pct = int(100 * total_score / total_possible) if total_possible > 0 else 0
    lines.append(f"📊 Overall score: {pct}%")
    lines.append("")

    # Per-policy table
    lines.append(f"{'Policy':<40} {'Score':<8} {'Critical Issues'}")
    lines.append(f"{'-'*40} {'-'*8} {'-'*30}")
    for a in sorted(valid_audits, key=lambda x: x.score):
        critical = a.critical_issues()
        critical_text = ", ".join(critical[:2]) if critical else "None"
        icon = "✅" if a.passed else "⚠️" if not critical else "❌"
        lines.append(f"{icon} {a.policy_name:<38} {a.score_label:<8} {critical_text}")

    # Top issues across all policies
    lines.append("")
    lines.append("Top Issues Across All Policies:")
    dimension_fails = {}
    for a in valid_audits:
        for dim in a.dimensions.values():
            if not dim.passed:
                dimension_fails.setdefault(dim.name, 0)
                dimension_fails[dim.name] += 1

    for i, (dim_name, count) in enumerate(
        sorted(dimension_fails.items(), key=lambda x: -x[1])[:5], 1
    ):
        pct = int(100 * count / len(valid_audits))
        lines.append(f"  {i}. {dim_name}: {count}/{len(valid_audits)} policies ({pct}%)")

    return "\n".join(lines)


def format_json(audits: list) -> str:
    """Format audits as JSON."""
    output = []
    for audit in audits:
        entry = {
            "file": audit.file_path,
            "policy": audit.policy_name,
            "score": audit.score,
            "total": audit.total,
            "passed": audit.passed,
        }
        if audit.parse_error:
            entry["parse_error"] = audit.parse_error
        else:
            entry["dimensions"] = {}
            for dim in audit.dimensions.values():
                entry["dimensions"][dim.name] = {
                    "status": dim.status,
                    "findings": [
                        {"level": level, "message": msg}
                        for level, msg in dim.findings
                    ],
                }
        output.append(entry)
    return json.dumps(output, indent=2)


# --- CLI ---

def main():
    parser = argparse.ArgumentParser(description="Audit Kyverno policies against best practices")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", help="Path to a single policy YAML file")
    group.add_argument("--dir", help="Path to a directory of policy YAML files")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--format", choices=["text", "json", "markdown"], default="text",
                        help="Output format (default: text)")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"❌ File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        audit = audit_single_policy(args.file, args.strict)
        if audit is None:
            print(f"⚠️  {args.file} is not a Kyverno policy — skipped.")
            sys.exit(0)
        audits = [audit]
    else:
        path = Path(args.dir)
        if not path.is_dir():
            print(f"❌ Directory not found: {args.dir}", file=sys.stderr)
            sys.exit(1)
        audits = audit_directory(args.dir, args.strict)

    if args.format == "json":
        print(format_json(audits))
    elif len(audits) == 1:
        print(format_single_text(audits[0]))
    else:
        print(format_batch_text(audits))

    # Exit code: 0 if all passed, 1 if any failed
    all_passed = all(a.passed for a in audits if not a.parse_error)
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
