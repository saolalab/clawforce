---
name: Testing
description: Write comprehensive tests using TDD, maintain test coverage, and follow testing best practices
emoji: 🧪
tags: [testing, tdd, unit-tests, integration-tests, e2e]
---

# Testing Skill

## Testing Pyramid

The testing pyramid represents the ideal distribution of tests:

```
        /\
       /  \      E2E Tests (few, slow, expensive)
      /____\
     /      \    Integration Tests (some, medium speed)
    /________\
   /          \  Unit Tests (many, fast, cheap)
  /____________\
```

### Unit Tests
- **What**: Test individual functions/methods in isolation
- **Speed**: Fast (milliseconds)
- **Quantity**: Many (80%+ of tests)
- **Scope**: Single function/class
- **Dependencies**: Mocked/stubbed
- **Example**: Test `calculateTotal()` with various inputs

### Integration Tests
- **What**: Test interactions between components/modules
- **Speed**: Medium (seconds)
- **Quantity**: Some (15% of tests)
- **Scope**: Multiple components working together
- **Dependencies**: Real databases, APIs, or services (may use test doubles)
- **Example**: Test API endpoint with database, test service layer with repository

### End-to-End (E2E) Tests
- **What**: Test complete user workflows
- **Speed**: Slow (minutes)
- **Quantity**: Few (5% of tests)
- **Scope**: Entire system
- **Dependencies**: Real infrastructure (or close to it)
- **Example**: Test user registration → login → purchase flow

## Test Naming Conventions

### Structure: `should [expected behavior] when [condition]`

**Good Examples**:
- `should return 0 when given empty array`
- `should throw error when user is not authenticated`
- `should calculate tax correctly when order total exceeds 100`
- `should send email when user signs up`

**Bad Examples**:
- `test1`, `testCalculate`, `testUser` (too vague)
- `should work` (doesn't describe behavior)
- `test_calculate_total_with_items` (missing "should" structure)

### Language-Specific Patterns

**JavaScript/TypeScript (Jest)**:
```javascript
describe('calculateTotal', () => {
  it('should return 0 when given empty array', () => {
    // ...
  });
  
  it('should sum all item prices correctly', () => {
    // ...
  });
});
```

**Python (pytest)**:
```python
def test_should_return_zero_when_given_empty_array():
    # ...

def test_should_sum_all_item_prices_correctly():
    # ...
```

**Go**:
```go
func TestCalculateTotal_ShouldReturnZeroWhenGivenEmptyArray(t *testing.T) {
    // ...
}
```

## Mocking Strategies

### When to Mock
- **External Services**: APIs, databases, file systems, network calls
- **Slow Operations**: Expensive computations, I/O operations
- **Unpredictable Behavior**: Random number generators, timestamps, user input
- **Side Effects**: Logging, email sending, notifications

### When NOT to Mock
- **Simple Value Objects**: Don't mock data structures, DTOs, or simple classes
- **Your Own Code**: Prefer real implementations unless they're slow/unstable
- **Third-Party Libraries**: Use real libraries unless they have side effects

### Mocking Patterns

**Dependency Injection**:
```python
class OrderService:
    def __init__(self, email_service, payment_gateway):
        self.email_service = email_service
        self.payment_gateway = payment_gateway
    
    def process_order(self, order):
        # Use self.email_service and self.payment_gateway
        pass

# In tests
def test_process_order():
    mock_email = Mock()
    mock_payment = Mock()
    service = OrderService(mock_email, mock_payment)
    # ...
```

**Stubs vs Mocks**:
- **Stub**: Returns predefined values, doesn't verify interactions
- **Mock**: Verifies that methods were called with expected arguments

```python
# Stub
mock_service.get_user.return_value = User(id=1, name="Alice")

# Mock (verify interaction)
mock_service.send_email.assert_called_once_with("alice@example.com", "Welcome")
```

## Coverage Targets

### Minimum Coverage
- **Critical Paths**: 90%+ (authentication, payment, data processing)
- **Business Logic**: 80%+ (core features, calculations)
- **Utilities/Helpers**: 70%+ (less critical, but still important)
- **Overall Project**: 80%+ (team standard)

### Measuring Coverage

**JavaScript/TypeScript**:
```bash
npm test -- --coverage
# or
jest --coverage
```

**Python**:
```bash
pytest --cov=src --cov-report=html
# or
coverage run -m pytest
coverage report
```

**Go**:
```bash
go test -cover
go test -coverprofile=coverage.out
go tool cover -html=coverage.out
```

### Coverage Reports
- Use HTML reports to identify untested code
- Focus on branch coverage, not just line coverage
- Don't aim for 100%—focus on meaningful tests

## TDD Workflow (Test-Driven Development)

### Red-Green-Refactor Cycle

1. **Red**: Write a failing test
   - Write the smallest test that describes desired behavior
   - Run it—it should fail (red)
   - This defines the interface and expected behavior

2. **Green**: Make the test pass
   - Write the minimal code to make the test pass
   - Don't worry about code quality yet
   - Run the test—it should pass (green)

3. **Refactor**: Improve the code
   - Now that tests pass, refactor for clarity/performance
   - Run tests again—they should still pass
   - Repeat cycle

### Example: TDD for `calculateTotal`

**Step 1: Red**
```python
def test_should_return_zero_when_given_empty_array():
    assert calculate_total([]) == 0
# Test fails: calculate_total doesn't exist
```

**Step 2: Green**
```python
def calculate_total(items):
    return 0
# Test passes!
```

**Step 3: Red (next test)**
```python
def test_should_sum_item_prices():
    items = [Item(price=10), Item(price=20)]
    assert calculate_total(items) == 30
# Test fails: returns 0
```

**Step 4: Green**
```python
def calculate_total(items):
    return sum(item.price for item in items)
# Both tests pass!
```

**Step 5: Refactor**
```python
def calculate_total(items):
    if not items:
        return 0
    return sum(item.price for item in items)
# Still passes, but clearer intent
```

### Benefits of TDD
- **Design**: Tests force you to think about the interface first
- **Confidence**: You know immediately if code works
- **Documentation**: Tests serve as executable documentation
- **Refactoring**: Tests give you confidence to refactor safely
- **Regression Prevention**: Tests catch bugs before they reach production

## Testing Best Practices

### Arrange-Act-Assert (AAA) Pattern
```python
def test_should_calculate_discount():
    # Arrange
    order = Order(total=100, customer_type="premium")
    expected_discount = 10
    
    # Act
    discount = calculate_discount(order)
    
    # Assert
    assert discount == expected_discount
```

### One Assertion Per Test (when possible)
- Makes failures clear—you know exactly what broke
- Exception: Related assertions that test one concept

### Test Independence
- Tests should not depend on each other
- Each test should be able to run in isolation
- Use `setUp`/`tearDown` or fixtures to prepare/clean up

### Test Data
- Use factories/builders for complex objects
- Prefer realistic test data over magic values
- Use constants for expected values

### Flaky Tests
- Avoid flaky tests (tests that sometimes pass, sometimes fail)
- Don't rely on timing, random data, or external services
- Use deterministic test data and mocked dependencies
