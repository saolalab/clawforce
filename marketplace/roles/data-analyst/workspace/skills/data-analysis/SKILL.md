---
name: Data Analysis
description: Comprehensive guide for conducting rigorous data analysis, from question definition to actionable recommendations
emoji: 📊
tags: [analysis, statistics, methodology, reporting]
---

# Data Analysis Skill

## Analysis Report Template

### Executive Summary
- **Question**: What business question are we answering?
- **Key Finding**: One-sentence summary of main insight
- **Recommendation**: Primary action item
- **Confidence**: High / Medium / Low

### Methodology
- **Data Sources**: Where did data come from?
- **Time Period**: What timeframe?
- **Sample Size**: How many observations?
- **Analytical Approach**: What methods used?
- **Assumptions**: What assumptions were made?

### Findings
- **Finding 1**: [Description]
  - Evidence: [Supporting data]
  - Confidence: [Statistical confidence]
- **Finding 2**: [Description]
  - Evidence: [Supporting data]
  - Confidence: [Statistical confidence]

### Recommendations
- **Priority 1**: [Action] - [Expected impact]
- **Priority 2**: [Action] - [Expected impact]

### Caveats
- **Limitations**: What are the limitations?
- **Biases**: Potential biases?
- **Data Quality**: Known data quality issues?
- **Next Steps**: What additional analysis needed?

## SQL Query Patterns

### Aggregation Patterns

**Daily Metrics**:
```sql
SELECT 
    DATE(created_at) as date,
    COUNT(*) as events,
    COUNT(DISTINCT user_id) as unique_users
FROM events
WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

**Cohort Analysis**:
```sql
WITH cohorts AS (
    SELECT 
        user_id,
        DATE_TRUNC('month', MIN(created_at)) as cohort_month
    FROM users
    GROUP BY user_id
)
SELECT 
    c.cohort_month,
    DATE_TRUNC('month', e.created_at) as event_month,
    COUNT(DISTINCT e.user_id) as active_users
FROM cohorts c
JOIN events e ON c.user_id = e.user_id
GROUP BY c.cohort_month, DATE_TRUNC('month', e.created_at)
ORDER BY c.cohort_month, event_month;
```

### Window Functions

**Running Totals**:
```sql
SELECT 
    date,
    revenue,
    SUM(revenue) OVER (ORDER BY date) as running_total
FROM daily_revenue
ORDER BY date;
```

**Ranking**:
```sql
SELECT 
    product_id,
    revenue,
    RANK() OVER (ORDER BY revenue DESC) as revenue_rank
FROM product_revenue;
```

**Period-over-Period Comparison**:
```sql
SELECT 
    date,
    revenue,
    LAG(revenue, 7) OVER (ORDER BY date) as revenue_7d_ago,
    revenue - LAG(revenue, 7) OVER (ORDER BY date) as change_7d
FROM daily_revenue
ORDER BY date;
```

### Common Table Expressions (CTEs)

**Multi-Step Analysis**:
```sql
WITH filtered_data AS (
    SELECT *
    FROM events
    WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
        AND status = 'completed'
),
aggregated AS (
    SELECT 
        DATE(created_at) as date,
        COUNT(*) as count
    FROM filtered_data
    GROUP BY DATE(created_at)
)
SELECT 
    date,
    count,
    AVG(count) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) as rolling_7d_avg
FROM aggregated
ORDER BY date;
```

## Statistical Test Selection Guide

### Comparing Means

**Two Groups (Independent)**:
- **Test**: Two-sample t-test
- **Assumptions**: Normal distribution, equal variances
- **When to use**: Comparing means between two groups (e.g., control vs treatment)

**Two Groups (Paired)**:
- **Test**: Paired t-test
- **Assumptions**: Normal distribution of differences
- **When to use**: Same subjects measured twice (e.g., before/after)

**Multiple Groups**:
- **Test**: ANOVA (Analysis of Variance)
- **Assumptions**: Normal distribution, equal variances, independence
- **When to use**: Comparing means across 3+ groups

### Categorical Data

**Two Categories**:
- **Test**: Chi-square test
- **Assumptions**: Expected frequencies > 5
- **When to use**: Testing independence between two categorical variables

**Multiple Categories**:
- **Test**: Chi-square test of independence
- **Assumptions**: Expected frequencies > 5
- **When to use**: Testing relationships between categorical variables

### Relationships

**Linear Relationship**:
- **Test**: Linear regression
- **Assumptions**: Linearity, independence, homoscedasticity, normality of residuals
- **When to use**: Predicting continuous outcome from continuous predictor

**Multiple Predictors**:
- **Test**: Multiple regression
- **Assumptions**: Same as linear regression
- **When to use**: Multiple predictors for one outcome

**Non-Linear Relationship**:
- **Test**: Non-linear regression or transformation
- **When to use**: Relationship is not linear

### Non-Parametric Alternatives

**When assumptions fail**:
- **Mann-Whitney U**: Alternative to two-sample t-test
- **Wilcoxon signed-rank**: Alternative to paired t-test
- **Kruskal-Wallis**: Alternative to ANOVA

## Data Quality Checklist

### Completeness
- [ ] Check for NULL values
- [ ] Identify missing time periods
- [ ] Verify expected record counts
- [ ] Check for gaps in sequences

### Accuracy
- [ ] Validate data ranges (min/max)
- [ ] Check for impossible values
- [ ] Verify calculations
- [ ] Cross-reference with source systems

### Consistency
- [ ] Check for duplicate records
- [ ] Verify referential integrity
- [ ] Validate data types
- [ ] Check for schema drift

### Freshness
- [ ] Verify last update timestamp
- [ ] Check pipeline execution logs
- [ ] Validate expected refresh cadence
- [ ] Identify stale data

### Outliers
- [ ] Identify statistical outliers (IQR method)
- [ ] Check for data entry errors
- [ ] Validate extreme values
- [ ] Document outlier handling

## A/B Test Analysis Template

### Hypothesis
- **Null Hypothesis**: [H₀]
- **Alternative Hypothesis**: [H₁]
- **Success Metric**: [Primary metric]
- **Minimum Detectable Effect**: [MDE]

### Test Design
- **Sample Size**: [Calculated sample size]
- **Duration**: [Test duration]
- **Traffic Split**: [A/B split ratio]
- **Randomization**: [Method used]

### Results

**Primary Metric**:
- **Control**: [Mean, CI]
- **Treatment**: [Mean, CI]
- **Difference**: [Absolute, Relative %]
- **P-value**: [Statistical significance]
- **Confidence Interval**: [95% CI]

**Secondary Metrics**:
- **[Metric Name]**: [Results]

### Statistical Analysis
- **Test Used**: [t-test / chi-square / etc.]
- **Power Analysis**: [Post-hoc power]
- **Multiple Comparisons**: [Correction applied?]

### Interpretation
- **Significant?**: Yes / No
- **Practical Significance**: [Is effect size meaningful?]
- **Confidence Level**: [How confident?]

### Recommendations
- **Action**: [Launch / Don't launch / Continue test]
- **Reasoning**: [Why?]
- **Next Steps**: [What to do next]

### Caveats
- **Limitations**: [What limits interpretation?]
- **Biases**: [Potential biases?]
- **External Factors**: [Any confounding factors?]
