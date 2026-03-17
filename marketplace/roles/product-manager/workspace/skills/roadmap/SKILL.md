---
name: roadmap
description: "Framework for product roadmap management, feature specification, prioritization, and release planning. Use when creating roadmaps, writing PRDs, prioritizing features, or planning releases."
metadata: {"clawbot":{"emoji":"🗺️"}}
---

# Product Roadmap Management

## Roadmap Template (Now/Next/Later)

```markdown
# Product Roadmap — Q{N} {YEAR}

## Now (This Quarter)
- **Feature 1**: {Brief description} — {Target launch date}
- **Feature 2**: {Brief description} — {Target launch date}
- **Feature 3**: {Brief description} — {Target launch date}

## Next (Next Quarter)
- **Feature 4**: {Brief description} — {Rationale}
- **Feature 5**: {Brief description} — {Rationale}

## Later (Future Exploration)
- **Feature 6**: {Brief description} — {Research needed}
- **Feature 7**: {Brief description} — {Research needed}
```

## Feature Specification Template (PRD)

```markdown
# Feature: {Feature Name}

## Problem Statement
- **User Problem**: {What problem are users facing?}
- **Business Problem**: {Why does this matter to the business?}
- **Evidence**: {Data, user quotes, research that supports this}

## Hypothesis
If we {build this feature}, then {expected outcome}, because {reasoning}.

## Solution
- **Overview**: {High-level description of the solution}
- **User Stories**:
  - As a {user type}, I want {action}, so that {benefit}
  - As a {user type}, I want {action}, so that {benefit}
- **Key Features**: (bulleted list)
- **Design Considerations**: {Notes for design team}

## Success Metrics
- **Primary Metric**: {Metric name} — Target: {target value}
- **Secondary Metrics**: 
  - {Metric name}: {target}
  - {Metric name}: {target}
- **How we'll measure**: {Data sources, analytics events}

## Edge Cases & Considerations
- {Edge case 1}: {How we'll handle it}
- {Edge case 2}: {How we'll handle it}
- **Technical Constraints**: {Any known limitations}
- **Dependencies**: {Other features or systems needed}

## Launch Plan
- **Beta**: {Date and user group}
- **Full Launch**: {Date}
- **Rollout Strategy**: {Gradual rollout? Feature flag?}
- **Marketing**: {Key messages and channels}
- **Support**: {Documentation, training needed}
```

## RICE Scoring Template

```markdown
## Feature Prioritization — RICE Scoring

| Feature | Reach | Impact | Confidence | Effort | Score | Rank |
|---------|-------|--------|------------|--------|-------|------|
| Feature A | {users/quarter} | {0.25-3} | {50-100%} | {person-months} | {calculated} | 1 |
| Feature B | {users/quarter} | {0.25-3} | {50-100%} | {person-months} | {calculated} | 2 |

**Scoring Guide**:
- **Reach**: Users affected per quarter
- **Impact**: 0.25 = minimal, 0.5 = low, 1 = medium, 2 = high, 3 = massive
- **Confidence**: 50% = low, 80% = medium, 100% = high
- **Effort**: Person-months (minimum 0.5)
- **Score**: (Reach × Impact × Confidence) / Effort
```

## Release Planning Checklist

- [ ] Features prioritized and scored
- [ ] PRDs written and reviewed
- [ ] Engineering estimates confirmed
- [ ] Design mockups approved
- [ ] Success metrics defined and tracked
- [ ] Launch plan documented
- [ ] Marketing materials prepared
- [ ] Support documentation ready
- [ ] Feature flags configured
- [ ] Rollback plan defined

## User Story Format

**Standard Format**: As a {user type}, I want {action}, so that {benefit}

**Example**: As a project manager, I want to filter tasks by assignee, so that I can quickly see what each team member is working on.

**Acceptance Criteria**:
- Given {context}, when {action}, then {expected outcome}
- Given {context}, when {action}, then {expected outcome}
