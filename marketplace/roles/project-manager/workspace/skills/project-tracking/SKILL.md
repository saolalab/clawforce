---
name: project-tracking
description: "Project status tracking and reporting. Use when monitoring progress, creating reports, or managing timelines."
metadata: {"clawbot":{"emoji":"📈"}}
---

# Project Tracking

## Status Report Template

```markdown
## Project Status: [Date]

### Summary
[One paragraph overview]

### RAG Status: 🟢/🟡/🔴

### Progress
- Completed: [X]%
- On track: [Yes/No]

### Key Accomplishments
- Achievement 1
- Achievement 2

### Upcoming Milestones
| Milestone | Due Date | Status |
|-----------|----------|--------|
| ... | ... | ... |

### Risks & Issues
| Item | Impact | Mitigation |
|------|--------|------------|
| ... | ... | ... |

### Blockers
- Blocker 1: [Status/Owner]

### Next Week Focus
- Priority 1
- Priority 2
```

## Agile Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| Velocity | Points per sprint | Stable |
| Burndown | Work remaining | Linear |
| Cycle Time | Start to done | Decreasing |
| Escaped Defects | Bugs in prod | Zero |

## Risk Management

### Risk Register Fields
- ID
- Description
- Probability (1-5)
- Impact (1-5)
- Score (P × I)
- Mitigation
- Owner
- Status

### Risk Response Strategies
- **Avoid**: Eliminate the threat
- **Mitigate**: Reduce probability/impact
- **Transfer**: Shift to third party
- **Accept**: Acknowledge and monitor
