# Example Policies for Testing

These policies are provided for testing the `kyverno-policy-auditor` Skill in Claude Code.

| File | Expected Score | Purpose |
|------|---------------|---------|
| `good-policy.yaml` | 6-7/8 | Well-structured policy with annotations, labels, autogen |
| `bad-policy.yaml` | 1-2/8 | Generic LLM output with 7 common issues |
| `medium-policy.yaml` | 4-5/8 | Missing severity, labels, and test coverage |
| `mutate-policy.yaml` | 5-6/8 | Mutate policy — tests background:false check |

## Test in Claude Code

```bash
# Install both Skills
cp -r kyverno-policy-auditor ~/.claude/skills/
cp -r kyverno-policy-generator ~/.claude/skills/

# Launch Claude Code
claude
```

### Test 1: Single policy audit

```
> "Audit the policy in kyverno-policy-auditor/examples/bad-policy.yaml"
```

Expected: Score 1/8 with findings on annotations, labels, safe defaults, autogen, patterns, messages, tests.

### Test 2: Batch audit

```
> "Audit all policies in kyverno-policy-auditor/examples/"
```

Expected: Batch report with overall score, per-policy scores, and top issues across all policies.

### Test 3: Cross-skill composition

```
> "Audit the policy in kyverno-policy-auditor/examples/good-policy.yaml and fix what's missing"
```

Expected: Auditor finds missing Chainsaw tests → automatically invokes `kyverno-policy-generator` to create them. No manual intervention between audit and generation.

### Test 4: Triggering separation

```
> "Create a Kyverno policy to block privileged containers"
```

Expected: Triggers `kyverno-policy-generator`, NOT the auditor. Confirms negative triggers work correctly when both Skills coexist.
