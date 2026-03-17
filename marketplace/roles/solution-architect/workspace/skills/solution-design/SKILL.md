---
name: solution-design
description: "Customer solution architecture and design. Use when designing implementations, creating architecture diagrams, or planning integrations."
metadata: {"clawbot":{"emoji":"🏗️"}}
---

# Solution Design

## Discovery Questions

### Business Context
- What problem are you trying to solve?
- What does success look like?
- Who are the stakeholders?
- What's the timeline?

### Technical Context
- What's your current architecture?
- What systems need to integrate?
- What are your constraints?
- What's your team's expertise?

## Solution Design Document

```markdown
## Solution Design: [Customer/Project]

### Executive Summary
[One paragraph overview]

### Requirements
#### Functional
- Requirement 1
- Requirement 2

#### Non-Functional
- Performance: [targets]
- Security: [requirements]
- Scalability: [needs]

### Architecture
[Diagram]

### Components
| Component | Purpose | Technology |
|-----------|---------|------------|
| ... | ... | ... |

### Integration Points
| System | Direction | Protocol | Data |
|--------|-----------|----------|------|
| ... | ... | ... | ... |

### Implementation Plan
1. Phase 1: [Scope]
2. Phase 2: [Scope]

### Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| ... | ... |
```

## Architecture Patterns

### Integration Patterns
- **API-first**: REST/GraphQL endpoints
- **Event-driven**: Webhooks, queues
- **Batch**: Scheduled data sync
- **Real-time**: WebSocket, streaming

### Deployment Options
- **SaaS**: Multi-tenant cloud
- **Single-tenant**: Dedicated instance
- **On-premise**: Customer infrastructure
- **Hybrid**: Split deployment
