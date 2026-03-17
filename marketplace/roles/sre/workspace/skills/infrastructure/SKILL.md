---
name: infrastructure
description: "Framework for managing infrastructure as code, deployments, disaster recovery, and scaling. Use when planning infrastructure changes, designing deployments, or responding to capacity issues."
metadata: {"clawbot":{"emoji":"🏗️"}}
---

# Infrastructure Management

Framework for managing infrastructure as code, deployments, and disaster recovery.

## Infrastructure as Code (IaC) Best Practices

### Principles

- **Version control everything** — All infrastructure configs in Git
- **Idempotent** — Running same config multiple times produces same result
- **Modular** — Reusable modules for common patterns
- **Documented** — README for each module, inline comments for complex logic
- **Tested** — Validate configs before applying (terraform validate, linting)

### Workflow

1. **Plan** — Review changes, estimate impact
2. **Validate** — Run validation/linting
3. **Review** — Code review for infrastructure changes
4. **Apply** — Deploy in stages (dev → staging → prod)
5. **Verify** — Confirm changes work as expected
6. **Document** — Update architecture docs

### Change Management

- **Small changes**: Direct PR, single reviewer
- **Medium changes**: PR with 2 reviewers, staging test
- **Large changes**: RFC, architecture review, staged rollout

## Deployment Strategies

### Blue-Green Deployment

- **Two identical environments**: Blue (current), Green (new)
- **Switch traffic** from Blue to Green instantly
- **Rollback**: Switch back to Blue if issues
- **Pros**: Zero downtime, instant rollback
- **Cons**: Requires 2x capacity during deployment

### Canary Deployment

- **Gradual rollout**: 5% → 25% → 50% → 100%
- **Monitor metrics** at each stage
- **Rollback**: Stop rollout if metrics degrade
- **Pros**: Risk mitigation, gradual validation
- **Cons**: Slower deployment, requires monitoring

### Rolling Deployment

- **Update instances** one at a time
- **Maintains capacity** during rollout
- **Rollback**: Stop rollout, revert remaining instances
- **Pros**: No capacity overhead
- **Cons**: Partial version running, slower rollback

### Feature Flags

- **Toggle features** without deployment
- **Gradual rollout**: Enable for % of users
- **Instant rollback**: Disable flag
- **A/B testing**: Compare feature variants

## Disaster Recovery Planning

### RTO/RPO Definitions

- **RTO (Recovery Time Objective)**: Max acceptable downtime
- **RPO (Recovery Point Objective)**: Max acceptable data loss

### Disaster Recovery Template

```markdown
# Disaster Recovery Plan: {Service/Component}

## RTO/RPO Targets
- **RTO**: {Time} (e.g., 1 hour)
- **RPO**: {Time} (e.g., 15 minutes)

## Failure Scenarios

### Scenario: {Failure Type}
- **Likelihood**: {High/Medium/Low}
- **Impact**: {Description}
- **Detection**: {How to detect}
- **Recovery Steps**:
  1. {Step 1}
  2. {Step 2}
  3. {Step 3}
- **Verification**: {How to verify recovery}
- **Prevention**: {How to prevent}

### Scenario: {Another Failure}
{Repeat structure}

## Backup Strategy
- **Frequency**: {Daily/Hourly/Continuous}
- **Retention**: {Duration}
- **Location**: {Primary/Secondary regions}
- **Verification**: {How backups are tested}

## Recovery Procedures
- **Failover**: {Steps to failover}
- **Failback**: {Steps to failback}
- **Data Restore**: {Steps to restore from backup}
```

## Change Management Checklist

Before making infrastructure changes:

- [ ] **Impact assessment** — What services/components affected?
- [ ] **Rollback plan** — How to revert if issues?
- [ ] **Testing** — Tested in dev/staging?
- [ ] **Documentation** — Runbook updated?
- [ ] **Communication** — Stakeholders notified?
- [ ] **Monitoring** — Alerts configured for new components?
- [ ] **Backup** — Backup/restore tested?
- [ ] **Approval** — Required approvals obtained?

## Scaling Playbook

### Horizontal Scaling (Scale Out)

**When to use:**
- Stateless services
- Need to handle more load
- Want redundancy

**How:**
- Add more instances
- Load balancer distributes traffic
- Auto-scaling based on metrics

**Metrics to monitor:**
- CPU utilization
- Request rate
- Queue depth

### Vertical Scaling (Scale Up)

**When to use:**
- Stateful services (databases)
- Single-instance bottlenecks
- Memory/CPU limits reached

**How:**
- Increase instance size
- More CPU, memory, disk
- May require downtime

**Metrics to monitor:**
- CPU utilization
- Memory usage
- Disk I/O

### Auto-Scaling Configuration

**Scale-up triggers:**
- CPU > 70% for 5 minutes
- Memory > 80% for 5 minutes
- Request rate > threshold
- Queue depth > threshold

**Scale-down triggers:**
- CPU < 30% for 15 minutes
- Request rate < threshold
- Ensure minimum instances maintained

**Best practices:**
- Set min/max instance limits
- Use multiple metrics (not just CPU)
- Scale up faster than scale down
- Test auto-scaling in staging

## Infrastructure Review Checklist

- [ ] **Security**: Secrets managed, access controls, encryption
- [ ] **Reliability**: Redundancy, failover, backups
- [ ] **Performance**: Capacity planning, scaling configured
- [ ] **Cost**: Right-sized instances, reserved instances, unused resources
- [ ] **Observability**: Monitoring, logging, alerting configured
- [ ] **Documentation**: Architecture docs, runbooks updated
- [ ] **Compliance**: Meets regulatory requirements
- [ ] **Disaster recovery**: DR plan tested, RTO/RPO met
