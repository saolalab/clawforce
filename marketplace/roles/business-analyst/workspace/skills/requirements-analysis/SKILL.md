---
name: requirements-analysis
description: "Requirements gathering and documentation. Use when eliciting, documenting, or validating requirements."
metadata: {"clawbot":{"emoji":"📋"}}
---

# Requirements Analysis

## Requirements Types

| Type | Description | Example |
|------|-------------|---------|
| Business | What the business needs | "Reduce processing time by 50%" |
| Functional | What the system does | "System shall calculate tax" |
| Non-functional | How the system performs | "Page loads in <2 seconds" |
| Constraints | Limitations | "Must use existing database" |

## Elicitation Techniques

- **Interviews**: One-on-one with stakeholders
- **Workshops**: Group sessions
- **Observation**: Watch users work
- **Document Analysis**: Review existing docs
- **Prototyping**: Show and iterate

## User Story Format

```
As a [role]
I want [feature]
So that [benefit]

Acceptance Criteria:
- Given [context]
- When [action]
- Then [outcome]
```

## Requirements Documentation

### Business Requirements Document (BRD)
- Executive summary
- Business objectives
- Scope and constraints
- Stakeholders
- Requirements list
- Success metrics

### Traceability Matrix

| Req ID | Description | Source | Priority | Status |
|--------|-------------|--------|----------|--------|
| REQ-001 | ... | Stakeholder A | High | Approved |

## Validation Checklist

- [ ] Stakeholders have reviewed
- [ ] Requirements are testable
- [ ] No conflicts between requirements
- [ ] Priorities are assigned
- [ ] Dependencies identified
