---
name: test-automation
description: "Test automation strategies and frameworks. Use when building, maintaining, or troubleshooting automated tests."
metadata: {"clawbot":{"emoji":"🤖"}}
---

# Test Automation

## Test Pyramid

```
      /\
     /E2E\        <- Few, slow, expensive
    /------\
   /Integration\  <- Some, medium speed
  /--------------\
 /   Unit Tests   \ <- Many, fast, cheap
/------------------\
```

## Test Types

| Type | Scope | Speed | Reliability |
|------|-------|-------|-------------|
| Unit | Single function/class | Fast | High |
| Integration | Multiple components | Medium | Medium |
| E2E | Full system | Slow | Lower |
| Performance | Load/stress | Varies | Medium |

## Automation Framework Selection

### Considerations
- Language compatibility
- Community support
- CI/CD integration
- Reporting capabilities
- Maintenance burden

### Common Frameworks
- **Unit**: Jest, Pytest, JUnit
- **Integration**: Supertest, TestContainers
- **E2E**: Playwright, Cypress, Selenium
- **API**: Postman, REST Assured

## Test Design Principles

### FIRST
- **Fast** — Tests run quickly
- **Independent** — No dependencies between tests
- **Repeatable** — Same result every time
- **Self-validating** — Pass or fail, no interpretation
- **Timely** — Written alongside code

### AAA Pattern
```python
def test_example():
    # Arrange - Set up test data
    user = create_test_user()
    
    # Act - Perform the action
    result = login(user.email, user.password)
    
    # Assert - Verify the outcome
    assert result.success == True
```

## Flaky Test Management

### Causes
- Timing/race conditions
- Shared state
- External dependencies
- Environment differences

### Solutions
- Add explicit waits
- Isolate test data
- Mock external services
- Use test containers

## Test Data Management

- **Factory patterns** — Generate test data
- **Fixtures** — Reusable setup
- **Seeding** — Consistent database state
- **Cleanup** — Reset after tests
