---
name: user-research
description: "Framework for conducting user research, creating personas, analyzing user needs, and competitive analysis. Use when planning research, conducting interviews, analyzing feedback, or evaluating competitors."
metadata: {"clawbot":{"emoji":"🔍"}}
---

# User Research

## User Interview Question Templates

### Discovery Interview (Problem Discovery)
- What problem are you trying to solve?
- How do you currently solve this problem?
- What's frustrating about your current solution?
- What would make your life easier?
- Walk me through a typical day when you encounter this problem.

### Feature Validation Interview
- How would you use this feature?
- What would make you want to use this?
- What concerns do you have?
- What's missing from this solution?
- Would you pay for this? How much?

### Post-Launch Interview
- Have you tried [feature]? What was your experience?
- What worked well? What didn't?
- What would make you use it more?
- Would you recommend it to others? Why or why not?

## Survey Design Guidelines

### Good Survey Questions
- **Start broad, narrow down** — General questions first, specific later
- **Use closed-ended for quantitative** — "On a scale of 1-5..."
- **Use open-ended for qualitative** — "Tell me about..."
- **Avoid leading questions** — "Don't you think X is great?" → "How do you feel about X?"
- **Keep it short** — 5-10 questions max for high completion rates

### Survey Template
```markdown
# Survey: {Topic}

1. How often do you {relevant action}? (Daily / Weekly / Monthly / Rarely / Never)
2. What's your biggest challenge with {topic}? (Open-ended)
3. How satisfied are you with {current solution}? (1-5 scale)
4. What feature would most improve your experience? (Multiple choice)
5. Any additional feedback? (Open-ended)
```

## Persona Template

```markdown
# Persona: {Persona Name}

## Demographics
- **Role**: {Job title/role}
- **Age**: {Range}
- **Location**: {Geographic context}
- **Company Size**: {If B2B}

## Goals
- {Primary goal 1}
- {Primary goal 2}
- {Primary goal 3}

## Pain Points
- {Pain point 1}
- {Pain point 2}
- {Pain point 3}

## Behaviors
- {How they currently solve problems}
- {Tools they use}
- {How they make decisions}

## Quote
"{Representative quote that captures their perspective}"

## How We Help
{How our product addresses their goals and pain points}
```

## Jobs-to-be-Done Framework

**Format**: When {situation}, I want to {motivation}, so I can {expected outcome}.

**Example**: When I'm planning a project, I want to see all team members' availability, so I can assign tasks without overloading anyone.

### Jobs-to-be-Done Categories
- **Functional Jobs**: What users are trying to accomplish
- **Emotional Jobs**: How users want to feel
- **Social Jobs**: How users want to be perceived

### Analysis Framework
1. **Job Statement**: Write the job statement
2. **Current Solutions**: What do users use today?
3. **Pain Points**: What's frustrating about current solutions?
4. **Desired Outcomes**: What would success look like?
5. **Constraints**: What prevents them from achieving the job?

## Competitive Analysis Template

```markdown
# Competitive Analysis: {Competitor Name}

## Overview
- **Product**: {Product name}
- **Company**: {Company name}
- **Pricing**: {Pricing model}
- **Target Users**: {Who they serve}

## Strengths
- {Strength 1}
- {Strength 2}
- {Strength 3}

## Weaknesses
- {Weakness 1}
- {Weakness 2}
- {Weakness 3}

## Key Features
- {Feature 1}: {How it works}
- {Feature 2}: {How it works}
- {Feature 3}: {How it works}

## User Feedback
- {Positive feedback theme}
- {Negative feedback theme}

## Our Differentiation
{How we're different or better}

## Opportunities
{Features they're missing that we could build}
```

## Research Synthesis

### Affinity Mapping
1. **Collect insights** — Quotes, observations, data points
2. **Group themes** — Cluster similar insights
3. **Identify patterns** — What themes emerge?
4. **Prioritize** — Which themes are most important?

### Insight Format
```markdown
## Insight: {Theme Name}

**Evidence**: {User quotes, data, observations}
**Frequency**: {How many users mentioned this}
**Impact**: {High/Medium/Low}
**Opportunity**: {What we could build}
```
