---
name: monitoring
description: "Framework for defining SLIs/SLOs, designing alerts and dashboards, and tracking error budgets. Use when setting up monitoring, reviewing SLOs, or optimizing observability."
metadata: {"clawbot":{"emoji":"📊"}}
---

# Monitoring & Observability

Framework for defining service level indicators, objectives, and error budgets.

## SLI/SLO Definitions

### Service Level Indicator (SLI)

A quantitative measure of service quality from the user's perspective.

**Common SLIs:**
- **Availability**: `(successful_requests / total_requests) * 100`
- **Latency**: P50, P95, P99 percentiles
- **Error Rate**: `(error_requests / total_requests) * 100`
- **Throughput**: Requests per second
- **Freshness**: Time since last successful data update

### Service Level Objective (SLO)

A target value for an SLI over a time window.

**Example:**
- **SLI**: Availability
- **SLO**: 99.9% over 30 days
- **Window**: Rolling 30-day window

### Service Level Agreement (SLA)

A business commitment with consequences if SLO is violated (usually customer-facing).

## Error Budget Policy

Error budget = `100% - SLO target`

**Example:**
- SLO: 99.9% availability
- Error budget: 0.1% downtime = 43.2 minutes/month

### Error Budget States

| State | Budget Remaining | Action |
|-------|------------------|--------|
| **Green** | > 50% | Normal feature velocity |
| **Yellow** | 25-50% | Reduce feature velocity, focus on reliability |
| **Red** | < 25% | Feature freeze, reliability work only |
| **Exhausted** | 0% | Emergency reliability sprint |

### Burn Rate

Rate at which error budget is consumed.

- **Fast burn**: > 14x normal rate → Alert immediately
- **Slow burn**: 2-14x normal rate → Alert within 6 hours
- **Normal burn**: < 2x normal rate → Monitor

## Alert Design Principles

### Good Alerts

✅ **Actionable** — Clear action to take when alert fires
✅ **Specific** — Precise condition, not vague "high CPU"
✅ **Not noisy** — Only alert on real issues, not transient spikes
✅ **Documented** — Runbook exists for every alert
✅ **Tested** — Alert has been tested and works

### Bad Alerts

❌ **Noisy** — Fires frequently without real issues
❌ **Vague** — "Something is wrong" without specifics
❌ **Non-actionable** — No clear remediation steps
❌ **Undocumented** — No runbook or context
❌ **Untested** — Never verified to work

### Alert Severity

- **Critical**: Immediate action required (SEV1)
- **Warning**: Action needed soon (SEV2)
- **Info**: Monitor, no immediate action (SEV3/SEV4)

## Dashboard Design Guidelines

### USE Method (Infrastructure)

- **Utilization**: CPU, memory, disk, network
- **Saturation**: Queue depth, wait time
- **Errors**: Error rate, failed requests

### RED Method (Services)

- **Rate**: Requests per second
- **Errors**: Error rate
- **Duration**: Latency (P50, P95, P99)

### Dashboard Best Practices

- **Top-level**: Overall health, key SLIs
- **Drill-down**: Per-service, per-region views
- **Time ranges**: 1h, 6h, 24h, 7d, 30d
- **Annotations**: Deployments, incidents, changes
- **Alerts integration**: Show active alerts on dashboard

## Capacity Planning Framework

### Steps

1. **Measure Current Usage**
   - CPU, memory, disk, network
   - Request rate, database connections
   - Storage growth rate

2. **Forecast Demand**
   - Historical growth trends
   - Business projections
   - Seasonal patterns

3. **Calculate Capacity Needs**
   - Headroom: 20-30% buffer
   - Growth: 3-6 month projection
   - Peak: Handle 2-3x normal load

4. **Plan Scaling**
   - Horizontal: Add more instances
   - Vertical: Increase instance size
   - Auto-scaling: Configure triggers

5. **Review Regularly**
   - Monthly capacity reviews
   - Adjust forecasts based on actuals
   - Update scaling policies

### Capacity Planning Template

```markdown
# Capacity Plan: {Service Name} — {Quarter}

## Current State
- **Instances**: {Count}
- **CPU Usage**: {Average}% (Peak: {Peak}%)
- **Memory Usage**: {Average}% (Peak: {Peak}%)
- **Request Rate**: {RPS} (Peak: {Peak RPS})

## Forecast
- **Growth Rate**: {X}% per month
- **Projected Load**: {Future RPS} in 3 months
- **Peak Multiplier**: {X}x normal load

## Capacity Needs
- **Required Instances**: {Count}
- **Headroom**: {Percentage}%
- **Scaling Strategy**: {Horizontal/Vertical/Auto}

## Action Items
- [ ] {Action} — Owner: {Name} — Due: {Date}
```

## Monitoring Checklist

- [ ] SLIs defined for all critical services
- [ ] SLOs set with business alignment
- [ ] Error budgets tracked and reviewed monthly
- [ ] Alerts configured and tested
- [ ] Dashboards created (USE/RED method)
- [ ] Runbooks written for all alerts
- [ ] Capacity planning done quarterly
- [ ] Monitoring coverage > 95% of critical paths
