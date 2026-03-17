---
name: tech-radar
description: "Framework for tracking and evaluating technology choices using a four-ring radar model. Use when evaluating new technologies, planning migrations, or maintaining the tech stack."
metadata: {"clawbot":{"emoji":"📡"}}
---

# Tech Radar

The Tech Radar organizes technologies into four rings based on adoption status:

## Four Rings

### Adopt
Technologies we use in production and recommend for new projects.

**Criteria**:
- Proven in production at scale
- Well-documented and maintained
- Team has expertise
- Low risk, high value

### Trial
Technologies we're experimenting with in non-critical projects.

**Criteria**:
- Promising but not yet proven
- Limited production experience
- Evaluating fit for our use case
- Small risk, potential high value

### Assess
Technologies worth exploring to understand potential value.

**Criteria**:
- Emerging or interesting
- Not yet evaluated
- May solve future problems
- Unknown risk/value

### Hold
Technologies we've decided not to adopt or are phasing out.

**Criteria**:
- Doesn't fit our needs
- Better alternatives exist
- Deprecated or unmaintained
- High risk or low value

## Evaluation Criteria

When assessing a new technology, evaluate:

1. **Maturity** — How long has it been around? Production-ready?
2. **Community** — Active maintainers? Good documentation? Stack Overflow presence?
3. **Performance** — Meets our performance requirements?
4. **Ecosystem** — Integrations, libraries, tooling available?
5. **Learning Curve** — How long to become productive?
6. **Vendor Lock-in** — Open source or proprietary? Portable?
7. **Cost** — Licensing, infrastructure, operational costs?
8. **Security** — Security track record? Regular updates?
9. **Team Fit** — Does the team have skills? Can we hire for it?

## Tech Radar Template

```markdown
# Tech Radar — {Quarter} {Year}

## Adopt
- {Technology} — {Brief reason}

## Trial
- {Technology} — {Brief reason, project using it}

## Assess
- {Technology} — {Brief reason, what we're exploring}

## Hold
- {Technology} — {Brief reason, migration plan if applicable}
```

## Migration Planning Template

When moving from Hold to Adopt (or adopting a replacement):

```markdown
# Migration Plan: {From Technology} → {To Technology}

## Current State
- **Usage**: {Where is it used?}
- **Dependencies**: {What depends on it?}
- **Risk**: {What breaks if we don't migrate?}

## Target State
- **Timeline**: {Target completion date}
- **Approach**: {Big bang | Gradual | Strangler pattern}
- **Success Criteria**: {How do we know it's done?}

## Migration Steps
1. {Step 1}
2. {Step 2}
3. {Step 3}

## Rollback Plan
{What if migration fails?}

## Timeline
- {Phase 1}: {Date range}
- {Phase 2}: {Date range}
- {Phase 3}: {Date range}
```
