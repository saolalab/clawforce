---
name: Code Quality
description: Maintain high code quality through reviews, refactoring, and standards enforcement
emoji: ✨
tags: [code-review, refactoring, standards, quality]
---

# Code Quality Skill

## Code Review Checklist

### Logic & Correctness
- [ ] Does the code solve the stated problem?
- [ ] Are edge cases handled (null, empty, overflow, underflow)?
- [ ] Are error conditions handled gracefully?
- [ ] Is the logic clear and easy to follow?
- [ ] Are there any obvious bugs or race conditions?

### Code Quality
- [ ] Is the code readable? Can a teammate understand it without explanation?
- [ ] Are functions/classes small and focused (single responsibility)?
- [ ] Is there unnecessary duplication? Can it be extracted?
- [ ] Are variable/function names descriptive and consistent?
- [ ] Is the code properly formatted and linted?

### Testing
- [ ] Are there tests for new functionality?
- [ ] Do tests cover happy paths, edge cases, and error conditions?
- [ ] Are tests readable and maintainable?
- [ ] Is test coverage adequate?
- [ ] Do tests run reliably (no flakiness)?

### Security
- [ ] Are user inputs validated and sanitized?
- [ ] Are sensitive operations properly authenticated/authorized?
- [ ] Are secrets/configs properly managed (not hardcoded)?
- [ ] Are SQL queries parameterized (no injection risks)?
- [ ] Are API endpoints rate-limited if needed?

### Performance
- [ ] Are there obvious performance issues (N+1 queries, unnecessary loops)?
- [ ] Is caching used appropriately?
- [ ] Are database queries optimized?
- [ ] Is memory usage reasonable?

### Documentation
- [ ] Are public APIs documented?
- [ ] Are complex algorithms/logic explained?
- [ ] Is the PR description clear (what, why, how)?
- [ ] Are breaking changes documented?

## PR Template

```markdown
## What
Brief description of what this PR does.

## Why
Why this change is needed (problem it solves, feature it adds).

## How
How the change was implemented (high-level approach, key decisions).

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] Edge cases tested

## Screenshots (if applicable)
[Add screenshots for UI changes]

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings generated
- [ ] Tests pass locally
```

## Refactoring Patterns

### Extract Method
**When**: Function is too long or does multiple things.
**How**: Identify a logical chunk, extract to a new function with a descriptive name.

```python
# Before
def process_order(order):
    # ... 50 lines of code ...
    total = sum(item.price * item.quantity for item in order.items)
    tax = total * 0.1
    shipping = 10 if total < 100 else 0
    final_total = total + tax + shipping
    # ... more code ...

# After
def calculate_total(order):
    total = sum(item.price * item.quantity for item in order.items)
    tax = total * 0.1
    shipping = 10 if total < 100 else 0
    return total + tax + shipping

def process_order(order):
    # ... other code ...
    final_total = calculate_total(order)
    # ... more code ...
```

### Replace Conditional with Polymorphism
**When**: Multiple if/else or switch statements based on type.
**How**: Create a base class/interface and move logic into subclasses.

```python
# Before
def calculate_price(item_type, base_price):
    if item_type == "book":
        return base_price * 0.9
    elif item_type == "electronics":
        return base_price * 1.1
    elif item_type == "food":
        return base_price

# After
class Item:
    def calculate_price(self, base_price): pass

class Book(Item):
    def calculate_price(self, base_price): return base_price * 0.9

class Electronics(Item):
    def calculate_price(self, base_price): return base_price * 1.1

class Food(Item):
    def calculate_price(self, base_price): return base_price
```

### Remove Dead Code
**When**: Unused functions, variables, imports, or commented-out code.
**How**: Delete it. Use version control if you need it later.

### Simplify Conditionals
**When**: Complex boolean logic or nested conditionals.
**How**: Extract to well-named variables or functions, use early returns.

```python
# Before
if user is not None and user.is_active and user.has_permission("read") and not user.is_banned:
    # ...

# After
can_read = user and user.is_active and user.has_permission("read") and not user.is_banned
if can_read:
    # ...
```

### Extract Constants
**When**: Magic numbers or strings appear multiple times.
**How**: Extract to named constants at module/class level.

```python
# Before
if status == "pending":
    timeout = 30
elif status == "processing":
    timeout = 60

# After
PENDING_TIMEOUT = 30
PROCESSING_TIMEOUT = 60

if status == "pending":
    timeout = PENDING_TIMEOUT
```

## Tech Debt Tagging Convention

Tag tech debt items in code comments or issue trackers:

- `[TECH-DEBT]`: General technical debt that should be addressed
- `[TECH-DEBT-HIGH]`: High-priority debt affecting performance, security, or maintainability
- `[TECH-DEBT-REFACTOR]`: Code that works but needs refactoring
- `[TECH-DEBT-TEST]`: Missing or inadequate tests
- `[TECH-DEBT-DOC]`: Missing or outdated documentation
- `[TECH-DEBT-PERF]`: Performance issues that need optimization

Example:
```python
# [TECH-DEBT-REFACTOR] This function is too long and does too much.
# Should be split into smaller functions. See issue #123.
def process_data(data):
    # ...
```

## Code Quality Metrics

- **Test Coverage**: Aim for 80%+ coverage on critical paths
- **Cyclomatic Complexity**: Keep functions under 10 complexity
- **Function Length**: Prefer functions under 50 lines
- **File Length**: Prefer files under 500 lines
- **Code Duplication**: Keep duplication under 5%
- **Linting Errors**: Zero errors, minimal warnings
