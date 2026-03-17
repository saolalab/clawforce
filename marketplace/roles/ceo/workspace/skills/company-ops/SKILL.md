---
name: company-ops
description: "Cross-functional company operations: status tracking, decision logging, and inter-department coordination. Use when managing company-wide processes."
metadata: {"clawbot":{"emoji":"🏢"}}
---

# Company Operations

## Decision Log

Record every significant decision in `.agents/memory/MEMORY.md` using this format:

```markdown
### Decision: {Title}
- **Date**: {YYYY-MM-DD}
- **Context**: {Why this decision was needed}
- **Options considered**: {List alternatives}
- **Decision**: {What was decided}
- **Owner**: {Who executes}
- **Review date**: {When to evaluate}
```

## Status Report Template

Request weekly status from each department lead:

```markdown
## {Department} Weekly Status — {Date}

### Completed
- (what shipped or was delivered)

### In Progress
- (active workstreams with % complete)

### Blocked
- (issues needing escalation)

### Next Week
- (planned priorities)
```

## Escalation Protocol

1. **P0 (Critical)**: Revenue impact or outage → immediate message to all leads
2. **P1 (High)**: Missed deadline or blocker → message to owner + their lead
3. **P2 (Medium)**: Risk identified → add to next sync agenda
4. **P3 (Low)**: Improvement opportunity → log for quarterly review

## Meeting Cadences

| Meeting | Frequency | Attendees | Purpose |
|---------|-----------|-----------|---------|
| All-hands | Monthly | Everyone | Alignment, wins, Q&A |
| Leadership sync | Weekly | Department leads | Cross-team coordination |
| 1:1 | Bi-weekly | CEO + each lead | Coaching, blockers |
| Board update | Quarterly | CEO + Board | Strategy, financials |
