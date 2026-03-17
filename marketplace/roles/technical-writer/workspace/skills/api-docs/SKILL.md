---
name: api-docs
description: "API documentation standards and practices. Use when documenting APIs, endpoints, or integrations."
metadata: {"clawbot":{"emoji":"🔌"}}
---

# API Documentation

## Endpoint Documentation Template

```markdown
## [Method] /path/to/endpoint

[Brief description of what this endpoint does]

### Authentication
Requires Bearer token in Authorization header.

### Request

#### Headers
| Header | Type | Required | Description |
|--------|------|----------|-------------|
| Authorization | string | Yes | Bearer token |

#### Path Parameters
| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Resource ID |

#### Query Parameters
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 20 | Max results |

#### Request Body
```json
{
  "name": "string",
  "email": "string"
}
```

### Response

#### Success (200)
```json
{
  "id": "123",
  "name": "Example",
  "created_at": "2024-01-01T00:00:00Z"
}
```

#### Error (400)
```json
{
  "error": "validation_error",
  "message": "Email is required"
}
```

### Example

```bash
curl -X POST https://api.example.com/users \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{"name": "John", "email": "john@example.com"}'
```
```

## OpenAPI Best Practices

### Operation IDs
Use consistent, descriptive operation IDs:
- `createUser`, `getUser`, `updateUser`, `deleteUser`
- `listOrders`, `getOrderById`

### Descriptions
- Endpoint description: What it does
- Parameter descriptions: What each param controls
- Response descriptions: What each status means

### Examples
Include realistic examples for:
- Request bodies
- Responses
- Error cases

## Error Documentation

| Status | Meaning | When Used |
|--------|---------|-----------|
| 400 | Bad Request | Invalid input |
| 401 | Unauthorized | Missing/invalid auth |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limited |
| 500 | Server Error | Internal error |

## SDK Documentation

### Quick Start
```markdown
## Installation

npm install @company/sdk

## Usage

import { Client } from '@company/sdk';

const client = new Client({ apiKey: 'your-key' });
const result = await client.resources.list();
```

### Method Documentation
- Purpose
- Parameters (with types)
- Return value
- Exceptions
- Example
