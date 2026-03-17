---
name: ticket-management
description: "Support ticket lifecycle management. Use when triaging, assigning, tracking, or resolving customer support tickets."
metadata: {"clawbot":{"emoji":"🎫"}}
---

# Ticket Management

## Ticket Lifecycle

```
New → Triaged → Assigned → In Progress → Resolved → Closed
                    ↓
              Escalated → [Engineering/Product/Other]
```

## Triage Framework

### Priority Levels

| Priority | Criteria | Response SLA | Resolution SLA |
|----------|----------|--------------|----------------|
| P0 - Critical | Service down, data loss, security breach | 15 minutes | 4 hours |
| P1 - High | Major feature broken, many users affected | 1 hour | 24 hours |
| P2 - Medium | Feature degraded, workaround available | 4 hours | 3 days |
| P3 - Low | Minor issue, cosmetic, feature request | 24 hours | 1 week |

### Triage Checklist

1. **Identify the issue** — What exactly is the customer reporting?
2. **Reproduce if possible** — Can we see the same behavior?
3. **Check known issues** — Is this a documented problem?
4. **Assess impact** — How many users affected? Business impact?
5. **Assign priority** — Based on impact and urgency
6. **Route appropriately** — Self-resolve, escalate, or delegate

## Ticket Template

```markdown
## Summary
[One-line description]

## Customer
- Account: [customer name/ID]
- Contact: [email/channel]
- Segment: [enterprise/SMB/self-serve]

## Issue Details
- **Reported**: [timestamp]
- **Priority**: [P0/P1/P2/P3]
- **Category**: [bug/question/feature-request/account]

## Description
[Detailed description from customer]

## Steps to Reproduce
1. [Step 1]
2. [Step 2]
3. [Expected vs actual result]

## Investigation Notes
[Your findings]

## Resolution
[How it was resolved]
```

## Escalation Criteria

Escalate when:
- You cannot reproduce or diagnose the issue
- The issue requires code changes
- Customer is threatening churn
- Security or data privacy is involved
- SLA is at risk

## Metrics to Track

- **First Response Time (FRT)** — Time to first human response
- **Time to Resolution (TTR)** — Total time from ticket open to close
- **First Contact Resolution (FCR)** — % resolved in first interaction
- **Customer Satisfaction (CSAT)** — Post-resolution survey score
- **Ticket Volume** — Trends by category, priority, time
