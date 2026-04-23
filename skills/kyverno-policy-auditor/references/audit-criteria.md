# Audit Criteria

Detailed criteria for each of the 8 audit dimensions.

## Scoring

- **✅ PASS** — Dimension fully meets best practices
- **⚠️ WARN** — Minor issues, policy works but could be improved
- **❌ FAIL** — Critical issues, policy may cause problems in production

## 1. Structure

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| apiVersion | `kyverno.io/v1` or `v2beta1` | — | Any other value |
| kind | `ClusterPolicy` or `Policy` | — | Any other value |
| name | Present, kebab-case | Uses underscores | Missing |
| rules | At least 1 rule defined | — | Empty or missing |

## 2. Annotations

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| title | Present and non-empty | — | Missing |
| category | Present and non-empty | — | Missing |
| severity | Valid value (low/medium/high/critical) | Non-standard value | Missing |
| description | Present, >20 chars | Present but short | Missing (strict mode) |
| subject | Present | Missing | — |
| minversion | Present | Missing | — |

## 3. Labels

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| managed-by | `app.kubernetes.io/managed-by` present | — | Missing |
| governance | Any kyverno/governance label present | No governance labels | — |

## 4. Safe Defaults

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| validationFailureAction | `Audit` | `Enforce` (flagged for review) | Invalid value |
| background (validate) | `true` | `false` or not set | — |
| background (mutate) | `false` | `true` | — |

## 5. Autogen Compatibility

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| match wrapper | Uses `match.any:` | Uses `match.resources:` without any | — |
| target kind | Pod (autogen covers all) | Deployment/StatefulSet directly | — |

## 6. Pattern Quality

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| Non-empty check | Uses `"?*"` | Uses `"*"` (allows empty) | — |
| Operators | All valid | — | Invalid operator (Contains, etc.) |
| forEach scope | Variables inside forEach only | message references element.* outside forEach | — |

## 7. Message Quality

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| Presence | Message defined | Missing on validate rule | — |
| Length | >20 chars | <20 chars | — |
| Actionable | Contains specific guidance | Generic ("required") | — |

## 8. Test Coverage

| Check | Pass | Warn | Fail |
|-------|------|------|------|
| Chainsaw test | Found alongside policy | — | Not found |
| Test resources | Both pass + block found | Only one found | Neither found |
