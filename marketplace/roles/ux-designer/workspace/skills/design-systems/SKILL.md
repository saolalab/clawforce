---
name: design-systems
description: "Design system management and component documentation. Use when creating, updating, or documenting design system components."
metadata: {"clawbot":{"emoji":"🎨"}}
---

# Design Systems

## Component Structure

```
Component/
├── Overview          # What and when to use
├── Anatomy           # Parts and naming
├── Variants          # States and variations
├── Guidelines        # Do's and don'ts
├── Accessibility     # A11y requirements
└── Code              # Implementation reference
```

## Design Token Categories

| Category | Examples |
|----------|----------|
| Colors | Primary, secondary, semantic, neutral |
| Typography | Font families, sizes, weights, line heights |
| Spacing | Margins, padding, gaps |
| Borders | Widths, radii, styles |
| Shadows | Elevation levels |
| Motion | Duration, easing |

## Component Documentation Template

```markdown
# [Component Name]

## Overview
Brief description of the component and its primary use case.

## When to Use
- Use case 1
- Use case 2

## When Not to Use
- Anti-pattern 1

## Anatomy
[Diagram showing component parts]

## Variants
### Primary
[Description and usage]

### Secondary
[Description and usage]

## States
- Default
- Hover
- Active
- Disabled
- Focus
- Error

## Accessibility
- Keyboard navigation requirements
- Screen reader considerations
- ARIA attributes

## Guidelines
### Do
- Best practice 1

### Don't
- Anti-pattern 1
```

## Consistency Checklist

- [ ] Uses design tokens, not hardcoded values
- [ ] Follows naming conventions
- [ ] Documented with all variants
- [ ] Accessibility reviewed
- [ ] Responsive behavior defined
- [ ] Motion/animation specified
