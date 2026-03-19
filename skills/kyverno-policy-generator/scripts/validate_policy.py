#!/usr/bin/env python3
"""
Kyverno Policy Validator
Validates generated Kyverno policies for correctness and best practices.

Usage:
    python validate_policy.py --file <policy.yaml>
    python validate_policy.py --file <policy.yaml> --strict

Checks performed:
    1. YAML syntax validation
    2. Required Kyverno fields (apiVersion, kind, spec.rules)
    3. Required annotations (title, category, severity, description)
    4. Autogen compatibility (targets Pod for auto-generation)
    5. Safe defaults (Audit mode, background scanning)
    6. Best practices (actionable error messages, proper patterns)
"""

import argparse
import sys
import yaml
from pathlib import Path

# Required Kyverno annotations
REQUIRED_ANNOTATIONS = [
    "policies.kyverno.io/title",
    "policies.kyverno.io/category",
    "policies.kyverno.io/severity",
    "policies.kyverno.io/description",
]

OPTIONAL_ANNOTATIONS = [
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


class ValidationResult:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.info = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def ok(self, msg):
        self.info.append(msg)

    @property
    def passed(self):
        return len(self.errors) == 0

    def summary(self):
        total = len(self.errors) + len(self.warnings) + len(self.info)
        return f"{len(self.info)} passed, {len(self.warnings)} warnings, {len(self.errors)} errors"


def validate_yaml_syntax(content: str, result: ValidationResult) -> dict | None:
    """Step 1: Validate YAML syntax."""
    try:
        docs = list(yaml.safe_load_all(content))
        if not docs or docs[0] is None:
            result.error("Empty YAML document")
            return None
        result.ok("YAML syntax valid")
        return docs[0]
    except yaml.YAMLError as e:
        result.error(f"YAML syntax error: {e}")
        return None


def validate_kyverno_structure(policy: dict, result: ValidationResult):
    """Step 2: Validate required Kyverno structure."""
    # Check apiVersion
    api = policy.get("apiVersion", "")
    if api in ("kyverno.io/v1", "kyverno.io/v2beta1"):
        result.ok(f"API version: {api}")
    else:
        result.error(f"Invalid apiVersion: '{api}'. Expected 'kyverno.io/v1' or 'kyverno.io/v2beta1'")

    # Check kind
    kind = policy.get("kind", "")
    if kind in ("ClusterPolicy", "Policy"):
        result.ok(f"Kind: {kind}")
    else:
        result.error(f"Invalid kind: '{kind}'. Expected 'ClusterPolicy' or 'Policy'")

    # Check metadata.name
    name = policy.get("metadata", {}).get("name", "")
    if name:
        result.ok(f"Policy name: {name}")
        if "_" in name:
            result.warn("Policy name uses underscores; dashes are preferred convention")
    else:
        result.error("Missing metadata.name")

    # Check spec.rules
    rules = policy.get("spec", {}).get("rules", [])
    if rules:
        result.ok(f"Rules defined: {len(rules)}")
    else:
        result.error("No rules defined in spec.rules")

    return rules


def validate_annotations(policy: dict, result: ValidationResult, strict: bool = False):
    """Step 3: Validate required annotations."""
    annotations = policy.get("metadata", {}).get("annotations", {})

    for ann in REQUIRED_ANNOTATIONS:
        if ann in annotations and annotations[ann]:
            result.ok(f"Annotation present: {ann}")
        else:
            if strict:
                result.error(f"Missing required annotation: {ann}")
            else:
                result.warn(f"Missing annotation: {ann}")

    # Validate severity value
    severity = annotations.get("policies.kyverno.io/severity", "")
    if severity and severity not in VALID_SEVERITIES:
        result.warn(f"Non-standard severity: '{severity}'. Expected: {VALID_SEVERITIES}")


def validate_rules(rules: list, policy: dict, result: ValidationResult):
    """Step 4: Validate individual rules."""
    spec = policy.get("spec", {})

    # Check validationFailureAction
    action = spec.get("validationFailureAction", "")
    if action:
        if action in VALID_ACTIONS:
            result.ok(f"Validation action: {action}")
            if action.lower() == "enforce":
                result.warn("Policy uses Enforce mode. Ensure this is intentional (Audit is safer for initial deployment)")
        else:
            result.error(f"Invalid validationFailureAction: '{action}'")

    # Check background
    background = spec.get("background")
    if background is True:
        result.ok("Background scanning enabled")
    elif background is False:
        result.ok("Background scanning disabled (expected for mutate/verifyImages)")

    for i, rule in enumerate(rules):
        rule_name = rule.get("name", f"rule-{i}")

        # Check rule has a name
        if "name" not in rule:
            result.error(f"Rule {i} missing 'name' field")

        # Check match clause
        if "match" not in rule:
            result.error(f"Rule '{rule_name}' missing 'match' clause")
        else:
            # Check for autogen compatibility
            match_resources = rule.get("match", {}).get("any", [{}])
            if match_resources:
                kinds = match_resources[0].get("resources", {}).get("kinds", [])
                if "Pod" in kinds:
                    result.ok(f"Rule '{rule_name}' targets Pod (autogen compatible)")
                elif kinds:
                    result.ok(f"Rule '{rule_name}' targets: {', '.join(kinds)}")

        # Check rule type
        rule_type = None
        for rt in VALID_RULE_TYPES:
            if rt in rule:
                rule_type = rt
                break

        if rule_type:
            result.ok(f"Rule '{rule_name}' type: {rule_type}")
        else:
            result.error(f"Rule '{rule_name}' has no valid rule type ({VALID_RULE_TYPES})")

        # Check validate rules have a message
        if rule_type == "validate":
            validate_block = rule.get("validate", {})
            if "message" in validate_block:
                msg = validate_block["message"]
                if len(msg) < 20:
                    result.warn(f"Rule '{rule_name}' has a very short error message. Make it actionable.")
                else:
                    result.ok(f"Rule '{rule_name}' has error message ({len(msg)} chars)")
            else:
                result.warn(f"Rule '{rule_name}' missing validate.message (recommended for clarity)")


def _collect_operators(obj, operators: list):
    """Recursively collect all operator values from a nested dict/list."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "operator" and isinstance(v, str):
                operators.append(v)
            else:
                _collect_operators(v, operators)
    elif isinstance(obj, list):
        for item in obj:
            _collect_operators(item, operators)


def validate_operators(rules: list, result: ValidationResult):
    """Check that all condition operators are valid Kyverno operators."""
    for rule in rules:
        rule_name = rule.get("name", "?")
        operators_found = []
        _collect_operators(rule, operators_found)
        for op in operators_found:
            if op not in VALID_OPERATORS:
                result.error(
                    f"Rule '{rule_name}': invalid operator '{op}'. "
                    f"Valid operators: {sorted(VALID_OPERATORS)}"
                )
            else:
                result.ok(f"Rule '{rule_name}': operator '{op}' is valid")


def validate_policy(file_path: str, strict: bool = False) -> ValidationResult:
    """Main validation pipeline."""
    result = ValidationResult()

    path = Path(file_path)
    if not path.exists():
        result.error(f"File not found: {file_path}")
        return result

    content = path.read_text()

    # Step 1: YAML syntax
    policy = validate_yaml_syntax(content, result)
    if policy is None:
        return result

    # Step 2: Kyverno structure
    rules = validate_kyverno_structure(policy, result)
    if not rules:
        return result

    # Step 3: Annotations
    validate_annotations(policy, result, strict)

    # Step 4: Rules
    validate_rules(rules, policy, result)

    # Step 5: Operators
    validate_operators(rules, result)

    return result


def main():
    parser = argparse.ArgumentParser(description="Validate Kyverno policy YAML")
    parser.add_argument("--file", required=True, help="Path to policy YAML file")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    result = validate_policy(args.file, args.strict)

    if args.json:
        import json
        output = {
            "file": args.file,
            "passed": result.passed,
            "summary": result.summary(),
            "errors": result.errors,
            "warnings": result.warnings,
            "info": result.info,
        }
        print(json.dumps(output, indent=2))
    else:
        print(f"\n🛡️  Kyverno Policy Validator")
        print(f"{'=' * 50}")
        print(f"📄 File: {args.file}")
        print()

        for msg in result.info:
            print(f"  ✅ {msg}")
        for msg in result.warnings:
            print(f"  ⚠️  {msg}")
        for msg in result.errors:
            print(f"  ❌ {msg}")

        print()
        print(f"📊 {result.summary()}")

        if result.passed:
            print(f"\n✅ Policy is valid and ready for deployment.")
            print(f"   Apply with: kubectl apply -f {args.file}")
        else:
            print(f"\n❌ Policy has errors. Please fix before deploying.")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
