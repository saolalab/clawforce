---
name: Data Pipeline Engineering
description: Guide for designing, building, and maintaining reliable data pipelines
emoji: 🔄
tags: [etl, pipelines, data-engineering, data-modeling]
---

# Data Pipeline Engineering Skill

## ETL Pipeline Design Checklist

### Extract Phase
- [ ] **Source Identification**: What are the data sources?
- [ ] **Extraction Method**: API, database query, file transfer?
- [ ] **Frequency**: Real-time, hourly, daily, batch?
- [ ] **Authentication**: How to authenticate?
- [ ] **Rate Limits**: Are there API rate limits?
- [ ] **Error Handling**: How to handle extraction failures?
- [ ] **Incremental vs Full**: Can we do incremental loads?

### Transform Phase
- [ ] **Data Cleaning**: What cleaning needed?
- [ ] **Validation Rules**: What validation checks?
- [ ] **Business Logic**: What transformations required?
- [ ] **Data Quality Checks**: Completeness, accuracy, consistency?
- [ ] **Deduplication**: How to handle duplicates?
- [ ] **Type Conversions**: What type conversions needed?
- [ ] **Aggregations**: Any aggregations required?

### Load Phase
- [ ] **Target System**: Where is data loaded?
- [ ] **Load Strategy**: Insert, update, upsert, replace?
- [ ] **Partitioning**: How to partition data?
- [ ] **Indexing**: What indexes needed?
- [ ] **Constraints**: What constraints to enforce?
- [ ] **Load Frequency**: How often to load?
- [ ] **Rollback Plan**: How to rollback if needed?

### Monitoring & Alerting
- [ ] **Success Metrics**: How to measure success?
- [ ] **Failure Alerts**: What failures to alert on?
- [ ] **Data Quality Alerts**: What quality issues to alert?
- [ ] **Performance Monitoring**: Track execution time?
- [ ] **Data Freshness**: Monitor data freshness?
- [ ] **Logging**: What to log?

### Documentation
- [ ] **Pipeline Documentation**: Documented pipeline?
- [ ] **Data Dictionary**: Updated data dictionary?
- [ ] **Runbook**: Operational runbook created?
- [ ] **Dependencies**: Documented dependencies?
- [ ] **Ownership**: Clear ownership assigned?

## Data Modeling Patterns

### Star Schema

**Structure**:
- One fact table (center)
- Multiple dimension tables (surrounding)
- Denormalized dimensions

**When to use**:
- OLAP workloads
- Simple queries
- Fast query performance needed
- Clear fact/dimension separation

**Example**:
```
Fact: sales
  - sale_id
  - date_id (FK)
  - product_id (FK)
  - customer_id (FK)
  - amount
  - quantity

Dimensions:
  - dim_date (date_id, date, month, year, quarter)
  - dim_product (product_id, name, category, price)
  - dim_customer (customer_id, name, region, segment)
```

### Snowflake Schema

**Structure**:
- Normalized dimensions
- Dimension tables reference other dimensions
- More normalized than star schema

**When to use**:
- Storage optimization needed
- Dimensions have hierarchies
- Dimension updates are frequent
- Acceptable to trade query performance for storage

**Example**:
```
Fact: sales
  - sale_id
  - date_id (FK)
  - product_id (FK)
  - customer_id (FK)
  - amount

Dimensions:
  - dim_date (date_id, date, month_id)
  - dim_month (month_id, month, quarter_id)
  - dim_quarter (quarter_id, quarter, year)
  - dim_product (product_id, name, category_id)
  - dim_category (category_id, category, department_id)
```

### One Big Table (OBT)

**Structure**:
- Single denormalized table
- All attributes in one table
- Pre-joined data

**When to use**:
- Simple analytics queries
- Small to medium datasets
- Query performance critical
- Storage not a concern

**Trade-offs**:
- ✅ Fast queries
- ✅ Simple structure
- ❌ Storage intensive
- ❌ Update complexity
- ❌ Data redundancy

## Data Dictionary Template

### Table: [table_name]

**Description**: [What this table contains]

**Schema**: [schema_name]

**Update Frequency**: [How often updated]

**Source**: [Where data comes from]

**Columns**:

| Column Name | Data Type | Nullable | Description | Example | Notes |
|------------|-----------|----------|-------------|---------|-------|
| column1 | VARCHAR(255) | No | [Description] | [Example] | [Notes] |
| column2 | INTEGER | Yes | [Description] | [Example] | [Notes] |

**Primary Key**: [column_name(s)]

**Foreign Keys**:
- [column] → [table.column]

**Indexes**:
- [index_name] on [columns]

**Business Rules**:
- [Rule 1]
- [Rule 2]

**Data Quality Checks**:
- [Check 1]
- [Check 2]

**Related Tables**:
- [Related table 1]
- [Related table 2]

## Pipeline Monitoring Checklist

### Freshness Monitoring
- [ ] **Expected Refresh Time**: When should data update?
- [ ] **Actual Refresh Time**: When did it actually update?
- [ ] **SLA**: What's the freshness SLA?
- [ ] **Alert Threshold**: Alert if > X hours late
- [ ] **Dashboard**: Show freshness status

### Completeness Monitoring
- [ ] **Expected Record Count**: How many records expected?
- [ ] **Actual Record Count**: How many received?
- [ ] **Completeness %**: (Actual / Expected) * 100
- [ ] **Alert Threshold**: Alert if < X% complete
- [ ] **Missing Data Detection**: Identify missing periods

### Accuracy Monitoring
- [ ] **Data Validation Rules**: What rules to check?
- [ ] **Range Checks**: Values within expected ranges?
- [ ] **Referential Integrity**: Foreign keys valid?
- [ ] **Business Logic Checks**: Values make business sense?
- [ ] **Anomaly Detection**: Statistical outlier detection

### Performance Monitoring
- [ ] **Execution Time**: Track pipeline runtime
- [ ] **Throughput**: Records processed per second
- [ ] **Resource Usage**: CPU, memory, I/O
- [ ] **Query Performance**: Slow query detection
- [ ] **Bottleneck Identification**: Identify slow steps

### Error Monitoring
- [ ] **Error Rate**: % of runs that fail
- [ ] **Error Types**: Categorize errors
- [ ] **Error Messages**: Log detailed errors
- [ ] **Retry Logic**: Automatic retry on failure?
- [ ] **Alert on Errors**: Alert on critical errors

## Migration Playbook Template

### Pre-Migration

**Planning**:
- [ ] **Scope**: What data/tables to migrate?
- [ ] **Timeline**: Migration schedule
- [ ] **Dependencies**: What depends on this?
- [ ] **Rollback Plan**: How to rollback?
- [ ] **Testing Plan**: How to test?

**Preparation**:
- [ ] **Backup**: Backup source data
- [ ] **Schema Creation**: Create target schema
- [ ] **Data Validation**: Validate source data
- [ ] **Test Migration**: Run test migration
- [ ] **Performance Testing**: Test query performance

### Migration Execution

**Steps**:
1. [ ] **Pre-Migration Checks**: Run validation
2. [ ] **Stop Writes**: Stop writes to source (if needed)
3. [ ] **Final Extract**: Extract final data
4. [ ] **Transform**: Apply transformations
5. [ ] **Load**: Load to target
6. [ ] **Validate**: Validate loaded data
7. [ ] **Switch Traffic**: Switch reads to target
8. [ ] **Monitor**: Monitor for issues

**Validation**:
- [ ] **Record Count**: Match source and target
- [ ] **Data Sampling**: Sample and compare
- [ ] **Query Results**: Compare query results
- [ ] **Performance**: Verify performance acceptable

### Post-Migration

**Verification**:
- [ ] **Data Integrity**: Verify data integrity
- [ ] **Query Performance**: Verify performance
- [ ] **User Acceptance**: Get user sign-off
- [ ] **Documentation**: Update documentation

**Cleanup**:
- [ ] **Archive Source**: Archive old data (if needed)
- [ ] **Update Dependencies**: Update dependent systems
- [ ] **Remove Old Pipeline**: Decommission old pipeline
- [ ] **Lessons Learned**: Document lessons learned

### Rollback Plan

**If Migration Fails**:
1. [ ] **Stop Migration**: Stop migration process
2. [ ] **Restore Source**: Restore source if needed
3. [ ] **Notify Stakeholders**: Alert stakeholders
4. [ ] **Investigate**: Investigate failure cause
5. [ ] **Fix Issues**: Fix identified issues
6. [ ] **Retry**: Retry migration (if appropriate)

## Best Practices

### Idempotency
- Design pipelines to be idempotent
- Can safely re-run without side effects
- Use upsert patterns where appropriate

### Incremental Processing
- Process only new/changed data when possible
- Use change data capture (CDC) if available
- Track last processed timestamp

### Error Handling
- Fail fast on critical errors
- Retry transient failures
- Log all errors with context
- Alert on persistent failures

### Testing
- Test with sample data first
- Validate transformations
- Test error scenarios
- Performance test at scale

### Documentation
- Document data lineage
- Keep data dictionary updated
- Document business rules
- Maintain runbooks
