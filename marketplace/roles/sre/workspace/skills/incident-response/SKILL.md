---
name: incident-response
description: "Framework for managing incidents from detection through postmortem. Use during active incidents, for creating runbooks, or when conducting postmortems."
metadata: {"clawbot":{"emoji":"🚨"}}
---

# Incident Response

Systematic framework for detecting, triaging, mitigating, and resolving incidents.

## Severity Levels

| Severity | Description | Response Time | Example |
|----------|-------------|---------------|---------|
| **SEV1** | Service down, data loss, security breach | < 15 minutes | Database unavailable, authentication broken |
| **SEV2** | Major degradation, partial outage | < 1 hour | API latency > 5s, 50% of users affected |
| **SEV3** | Minor degradation, non-critical | < 4 hours | Single feature broken, workaround available |
| **SEV4** | Cosmetic, non-user-facing | < 1 business day | UI typo, non-critical log errors |

## Incident Commander Checklist

When leading an incident:

- [ ] **Declare incident** — Create incident channel, assign severity, notify stakeholders
- [ ] **Assess impact** — Affected services, user count, business impact
- [ ] **Form response team** — Assign roles (commander, scribe, engineers)
- [ ] **Establish timeline** — Document all actions and observations
- [ ] **Mitigate** — Take immediate actions to restore service
- [ ] **Communicate** — Send status updates every 15-30 minutes
- [ ] **Resolve** — Verify fix, monitor for stability
- [ ] **Postmortem** — Schedule within 48 hours, document learnings

## Communication Templates

### Initial Incident Alert

```
🚨 SEV{1-4} Incident: {Service Name} - {Brief Description}

Impact: {User count / % of traffic / Business impact}
Status: Investigating
Timeline:
- {Time} - Incident detected
- {Time} - Response team assembled

Next update in 15 minutes.
```

### Status Update

```
📊 SEV{1-4} Update: {Service Name}

Status: {Investigating / Mitigating / Resolved}
Impact: {Updated impact assessment}
Actions taken:
- {Action 1}
- {Action 2}
Next update: {Time}
```

### Customer Communication (for SEV1/SEV2)

```
We're currently experiencing issues with {Service Name} that may affect {specific functionality}.

We're actively working on a fix and will provide updates every {interval}.

Status page: {URL}
```

### Resolution Notice

```
✅ SEV{1-4} Resolved: {Service Name}

Issue: {Root cause summary}
Resolution: {What fixed it}
Prevention: {Action items to prevent recurrence}
Postmortem: {Link to postmortem doc}
```

## Postmortem Template

```markdown
# Postmortem: {Incident Name} — {Date}

## Summary
- **Severity**: SEV{1-4}
- **Duration**: {Start time} to {End time} ({Duration})
- **Impact**: {Users affected, revenue impact, etc.}
- **Status**: Resolved

## Timeline

| Time | Event | Action Taken |
|------|-------|--------------|
| {Time} | {Event} | {Action} |
| {Time} | {Event} | {Action} |

## Root Cause

{Detailed explanation of what went wrong and why}

## Contributing Factors

- {Factor 1}
- {Factor 2}

## Impact Assessment

- **Users Affected**: {Number/percentage}
- **Revenue Impact**: {If applicable}
- **Reputation Impact**: {If applicable}

## Action Items

- [ ] {Action item} — Owner: {Name} — Due: {Date}
- [ ] {Action item} — Owner: {Name} — Due: {Date}

## Lessons Learned

- {Lesson 1}
- {Lesson 2}

## Prevention Measures

- {Measure 1}
- {Measure 2}
```

## Runbook Template

```markdown
# Runbook: {Service/Component Name}

## Overview
{What this service does, dependencies, critical paths}

## Monitoring
- **Dashboard**: {URL}
- **Key Metrics**: {List critical metrics}
- **Alerts**: {Alert names and thresholds}

## Common Issues

### Issue: {Symptom}
**Severity**: SEV{1-4}
**Detection**: {How to detect}
**Root Causes**:
- {Cause 1}
- {Cause 2}

**Resolution Steps**:
1. {Step 1}
2. {Step 2}
3. {Step 3}

**Verification**: {How to verify fix}
**Prevention**: {How to prevent}

### Issue: {Another Symptom}
{Repeat structure}
```

## Blameless Postmortem Principles

- Focus on **what** happened, not **who** did it
- Assume good intentions — people don't cause incidents intentionally
- Look for **systemic** issues, not individual mistakes
- Every incident is a learning opportunity
- Document action items, not blame

## Escalation Path

1. **On-Call Engineer** — First responder
2. **SRE Lead** — For SEV1/SEV2 or when stuck
3. **CTO** — For architecture decisions or critical escalations
4. **CEO** — For business-critical incidents affecting customers
