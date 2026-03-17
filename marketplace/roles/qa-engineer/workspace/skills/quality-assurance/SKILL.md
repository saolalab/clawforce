---
name: quality-assurance
description: "Quality assurance processes and methodologies. Use when planning testing, managing bugs, or improving quality."
metadata: {"clawbot":{"emoji":"✅"}}
---

# Quality Assurance

## QA in SDLC

```
Requirements → Design → Development → Testing → Release
     ↑            ↑           ↑          ↑        ↑
   Review     Review     Code Review   QA     Monitoring
```

## Bug Report Template

```markdown
## Bug Report

### Summary
[One-line description]

### Environment
- Browser/OS: 
- Version:
- User type:

### Steps to Reproduce
1. Go to [page]
2. Click [element]
3. Enter [data]
4. Observe [behavior]

### Expected Result
[What should happen]

### Actual Result
[What actually happens]

### Severity
- [ ] Critical - System unusable
- [ ] Major - Feature broken
- [ ] Minor - Workaround available
- [ ] Cosmetic - Visual issue

### Attachments
[Screenshots, logs, video]
```

## Test Case Template

```markdown
## Test Case: [ID]

### Title
[Brief description]

### Preconditions
- User is logged in
- [Other setup]

### Test Steps
| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Navigate to page | Page loads |
| 2 | Click button | Modal opens |

### Test Data
- Username: test@example.com
- [Other data]

### Priority
High/Medium/Low

### Type
Functional/Regression/Smoke
```

## Testing Techniques

### Equivalence Partitioning
Divide inputs into groups that should behave the same.

### Boundary Value Analysis
Test at the edges of valid ranges.

### Decision Table
Cover all combinations of conditions.

### Exploratory Testing
Session-based testing with a charter.

## Quality Metrics

| Metric | Formula | Target |
|--------|---------|--------|
| Defect Density | Bugs / KLOC | < 1 |
| Test Coverage | Covered / Total | > 80% |
| Defect Escape | Prod bugs / Total bugs | < 5% |
| Pass Rate | Passed / Total tests | > 95% |
