---
name: architecture-review
description: "Framework for reviewing system architecture, creating RFCs, documenting ADRs, and managing tech debt. Use when evaluating architecture changes, reviewing designs, or making technical decisions."
metadata: {"clawbot":{"emoji":"🏗️"}}
---

# Architecture Review

## RFC Template

Use this template for Request for Comments on significant architecture changes:

```markdown
# RFC: {Title}

## Context

{Why is this change needed? What problem does it solve?}

## Options Considered

### Option A: {Name}
- **Pros**: {list}
- **Cons**: {list}
- **Cost**: {estimate}
- **Timeline**: {estimate}

### Option B: {Name}
- **Pros**: {list}
- **Cons**: {list}
- **Cost**: {estimate}
- **Timeline**: {estimate}

## Decision

{Which option was chosen and why}

## Consequences

- **Positive**: {expected benefits}
- **Negative**: {trade-offs and risks}
- **Neutral**: {side effects}
```

## ADR Template

Architecture Decision Records document key technical choices:

```markdown
# ADR {Number}: {Title}

**Status**: {Proposed | Accepted | Rejected | Deprecated | Superseded}

**Date**: {YYYY-MM-DD}

## Context

{What is the issue we're addressing?}

## Decision

{What is the change we're proposing or have agreed to?}

## Consequences

{What becomes easier or more difficult? What are the trade-offs?}

## Alternatives Considered

- {Alternative 1}: {Why it was rejected}
- {Alternative 2}: {Why it was rejected}
```

## System Design Review Checklist

When reviewing a system design, evaluate against these dimensions:

### Scalability
- [ ] Can it handle 10x current load?
- [ ] What are the bottlenecks?
- [ ] Is horizontal scaling possible?
- [ ] Are there stateful components that limit scaling?

### Reliability
- [ ] What is the expected uptime target?
- [ ] How are failures handled?
- [ ] What are single points of failure?
- [ ] Is there redundancy at critical layers?

### Security
- [ ] How is authentication/authorization handled?
- [ ] Are secrets properly managed?
- [ ] Is data encrypted in transit and at rest?
- [ ] What are the attack surfaces?
- [ ] Is input validation comprehensive?

### Observability
- [ ] What metrics are tracked?
- [ ] How are errors logged and alerted?
- [ ] Can we trace requests across services?
- [ ] Is there sufficient visibility for debugging?

### Cost
- [ ] What is the infrastructure cost?
- [ ] Are there licensing fees?
- [ ] What is the operational overhead?
- [ ] How does cost scale with usage?

## Tech Debt Scoring Framework

Rate tech debt items on a 1-5 scale:

| Dimension | 1 (Low) | 3 (Medium) | 5 (High) |
|-----------|---------|------------|----------|
| **Impact** | Minor inconvenience | Affects productivity | Blocks features |
| **Risk** | Low risk of failure | Moderate risk | High risk of outage |
| **Effort** | < 1 day | 1-3 days | > 1 week |
| **Urgency** | Can wait months | Should address this quarter | Needs immediate attention |

**Priority Score** = (Impact + Risk + Urgency) / 3

**Total Score** = Priority Score × Effort

Use Total Score to prioritize tech debt backlog.
