---
name: integration-patterns
description: "Integration patterns and API design. Use when designing integrations, APIs, or data flows."
metadata: {"clawbot":{"emoji":"🔗"}}
---

# Integration Patterns

## Common Patterns

### Request-Response (Sync)
```
Client → API → Process → Response
```
Use for: Real-time queries, CRUD operations

### Event-Driven (Async)
```
Producer → Event Bus → Consumer(s)
```
Use for: Notifications, loose coupling

### Webhook
```
Source System → HTTP POST → Target System
```
Use for: Real-time notifications, triggers

### Batch/ETL
```
Source → Extract → Transform → Load → Target
```
Use for: Large data volumes, periodic sync

## API Design Guidelines

### RESTful Conventions
- `GET /resources` - List
- `GET /resources/{id}` - Get one
- `POST /resources` - Create
- `PUT /resources/{id}` - Replace
- `PATCH /resources/{id}` - Update
- `DELETE /resources/{id}` - Delete

### Versioning Strategies
- URL: `/v1/resources`
- Header: `Accept: application/vnd.api+json;version=1`
- Query: `/resources?version=1`

## Data Mapping

### Transformation Template
```
Source Field    → Target Field    Transformation
customer_id     → customerId      Direct
created_at      → createdAt       ISO 8601 format
status          → status          Map: 1→active, 2→inactive
```

## Error Handling

### Retry Strategy
- Exponential backoff
- Max retry limit
- Dead letter queue

### Idempotency
- Use idempotency keys
- Design for "at least once"
- Handle duplicates gracefully
