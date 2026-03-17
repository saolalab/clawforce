---
name: growth-analytics
description: "Frameworks and templates for marketing analytics including funnel metrics, campaign performance reports, SEO audits, A/B testing, attribution models, and marketing KPIs. Use when analyzing performance, optimizing campaigns, or reporting results."
metadata: {"clawbot":{"emoji":"📊"}}
---

# Growth Analytics

## Marketing Funnel Metrics

### Top of Funnel (TOFU) - Awareness
**Goal**: Attract and educate potential customers

**Key Metrics**:
- **Impressions**: Total views of your content/ads
- **Reach**: Unique users who saw your content
- **Traffic**: Website visitors, blog readers
- **Social Followers**: Growth rate, engagement rate
- **Brand Mentions**: Volume, sentiment, share of voice
- **Cost per Impression (CPM)**: Ad spend / impressions × 1000

**Target Benchmarks**:
- Blog traffic growth: [X]% MoM
- Social follower growth: [X]% MoM
- Brand mention volume: [X] mentions/month

### Middle of Funnel (MOFU) - Consideration
**Goal**: Nurture leads and build interest

**Key Metrics**:
- **Email Subscribers**: Growth rate, open rate, click rate
- **Content Engagement**: Time on page, scroll depth, downloads
- **Lead Magnets**: Downloads, sign-ups, form submissions
- **Marketing Qualified Leads (MQLs)**: Leads that meet qualification criteria
- **Cost per Lead (CPL)**: Total marketing spend / number of leads
- **Lead-to-MQL Rate**: MQLs / Total leads × 100

**Target Benchmarks**:
- Email open rate: [X]% (industry average: 20-25%)
- Email click rate: [X]% (industry average: 2-5%)
- MQL conversion rate: [X]% of leads

### Bottom of Funnel (BOFU) - Decision
**Goal**: Convert leads to customers

**Key Metrics**:
- **Sales Qualified Leads (SQLs)**: MQLs accepted by sales
- **Conversion Rate**: Conversions / visitors × 100
- **Cost per Acquisition (CAC)**: Total marketing spend / new customers
- **Customer Acquisition Cost (CAC)**: Marketing + Sales spend / new customers
- **Lifetime Value (LTV)**: Average revenue per customer over lifetime
- **LTV:CAC Ratio**: Should be 3:1 or higher
- **Sales Cycle Length**: Time from first touch to close

**Target Benchmarks**:
- Conversion rate: [X]% (varies by industry)
- CAC payback period: [X] months
- LTV:CAC ratio: 3:1 or higher

## Campaign Performance Report Template

```markdown
# Campaign Performance Report: [Campaign Name]

**Period**: [Start Date] - [End Date]
**Status**: [Active/Completed/Paused]

## Executive Summary
- **Objective**: [What we set out to achieve]
- **Results**: [Key outcomes in 2-3 sentences]
- **ROI**: [Return on investment]

## Campaign Overview
- **Budget**: $[Amount]
- **Spend**: $[Amount]
- **Channels**: [List channels used]
- **Target Audience**: [Description]

## Key Metrics

### Awareness Metrics
- Impressions: [Number]
- Reach: [Number]
- CPM: $[Amount]

### Engagement Metrics
- Clicks: [Number]
- CTR: [X]%
- Engagement Rate: [X]%

### Conversion Metrics
- Leads Generated: [Number]
- Cost per Lead: $[Amount]
- Conversion Rate: [X]%
- Customers Acquired: [Number]
- CAC: $[Amount]

### Revenue Metrics
- Revenue Generated: $[Amount]
- ROI: [X]%
- LTV: $[Amount]

## Channel Performance

### [Channel 1]
- Spend: $[Amount]
- Impressions: [Number]
- Clicks: [Number]
- Conversions: [Number]
- CAC: $[Amount]

### [Channel 2]
[Repeat structure]

## Insights & Learnings
- **What Worked**: [Key successes]
- **What Didn't Work**: [Challenges or failures]
- **Surprises**: [Unexpected findings]

## Recommendations
- **Continue**: [What to keep doing]
- **Optimize**: [What to improve]
- **Stop**: [What to discontinue]
- **Test**: [New ideas to try]

## Next Steps
- [Action item 1]
- [Action item 2]
- [Action item 3]
```

## SEO Audit Checklist

```markdown
# SEO Audit Checklist

## Technical SEO
- [ ] Site speed (Core Web Vitals)
- [ ] Mobile responsiveness
- [ ] SSL certificate (HTTPS)
- [ ] XML sitemap
- [ ] Robots.txt
- [ ] Canonical tags
- [ ] 404 error pages
- [ ] Broken links
- [ ] URL structure
- [ ] Schema markup

## On-Page SEO
- [ ] Title tags (50-60 characters, include keyword)
- [ ] Meta descriptions (150-160 characters)
- [ ] H1 tags (one per page, include keyword)
- [ ] H2/H3 structure (logical hierarchy)
- [ ] Keyword optimization (natural, not stuffed)
- [ ] Image alt text
- [ ] Internal linking
- [ ] External linking (authoritative sources)
- [ ] Content length (1,500+ words for blog posts)

## Content Quality
- [ ] Original, valuable content
- [ ] Regular publishing schedule
- [ ] Content freshness (updated regularly)
- [ ] User intent alignment
- [ ] Readability (Flesch score)

## Off-Page SEO
- [ ] Backlink profile (quality and quantity)
- [ ] Domain authority
- [ ] Social signals
- [ ] Local SEO (if applicable)
- [ ] Brand mentions

## Analytics & Tracking
- [ ] Google Analytics setup
- [ ] Google Search Console
- [ ] Goal tracking
- [ ] Conversion tracking
- [ ] Keyword ranking tracking
```

## A/B Testing Framework

```markdown
# A/B Test Plan: [Test Name]

## Hypothesis
**If** [change], **then** [expected outcome], **because** [reasoning]

## Test Details
- **Variable**: [What you're testing]
- **Control**: [Version A - current]
- **Variant**: [Version B - new]
- **Traffic Split**: [50/50 or other]
- **Duration**: [X days/weeks]
- **Sample Size**: [Minimum visitors needed]

## Success Metrics
- **Primary Metric**: [Main KPI to measure]
- **Secondary Metrics**: [Additional metrics]
- **Statistical Significance**: [Target: 95% confidence]

## Results

### Version A (Control)
- [Metric 1]: [Value]
- [Metric 2]: [Value]
- Conversion Rate: [X]%

### Version B (Variant)
- [Metric 1]: [Value]
- [Metric 2]: [Value]
- Conversion Rate: [X]%

### Analysis
- **Winner**: [A or B]
- **Lift**: [X]% improvement
- **Confidence**: [X]% (statistically significant if >95%)
- **Insights**: [What we learned]

## Recommendation
- [Implement winner / Run another test / No significant difference]
```

## Attribution Model Overview

### First-Touch Attribution
- **Definition**: 100% credit to first touchpoint
- **Use Case**: Understanding awareness channels
- **Best For**: Top-of-funnel analysis

### Last-Touch Attribution
- **Definition**: 100% credit to last touchpoint before conversion
- **Use Case**: Understanding conversion channels
- **Best For**: Bottom-of-funnel analysis

### Linear Attribution
- **Definition**: Equal credit to all touchpoints
- **Use Case**: Balanced view of customer journey
- **Best For**: Multi-touch campaigns

### Time-Decay Attribution
- **Definition**: More credit to touchpoints closer to conversion
- **Use Case**: Weighting recent interactions
- **Best For**: Long sales cycles

### Position-Based Attribution
- **Definition**: 40% first touch, 40% last touch, 20% middle touches
- **Use Case**: Balancing awareness and conversion
- **Best For**: Full-funnel campaigns

### Data-Driven Attribution
- **Definition**: Credit based on machine learning analysis
- **Use Case**: Most accurate attribution
- **Best For**: Advanced analytics (requires sufficient data)

## Marketing KPI Dashboard Template

```markdown
# Marketing KPI Dashboard: [Month/Quarter]

## Funnel Metrics

### Awareness (TOFU)
- Website Traffic: [Number] ([X]% MoM)
- Blog Traffic: [Number] ([X]% MoM)
- Social Followers: [Number] ([X]% MoM)
- Brand Mentions: [Number] ([X]% MoM)

### Consideration (MOFU)
- Email Subscribers: [Number] ([X]% MoM)
- MQLs: [Number] ([X]% MoM)
- Lead-to-MQL Rate: [X]%
- Cost per Lead: $[Amount]

### Conversion (BOFU)
- SQLs: [Number] ([X]% MoM)
- Customers Acquired: [Number] ([X]% MoM)
- Conversion Rate: [X]%
- CAC: $[Amount]

## Channel Performance

### Owned Channels
- Blog: [Traffic, Engagement, Leads]
- Email: [Subscribers, Open Rate, Click Rate, Conversions]
- Social: [Followers, Engagement Rate, Clicks, Conversions]

### Paid Channels
- Google Ads: [Spend, Impressions, Clicks, Conversions, CAC]
- Social Ads: [Spend, Impressions, Clicks, Conversions, CAC]
- Other: [Channel-specific metrics]

## Financial Metrics
- Marketing Spend: $[Amount]
- Revenue Generated: $[Amount]
- ROI: [X]%
- CAC: $[Amount]
- LTV: $[Amount]
- LTV:CAC Ratio: [X]:1
- CAC Payback Period: [X] months

## Content Performance
- Blog Posts Published: [Number]
- Top Performing Posts: [List top 3-5]
- Average Engagement: [Time on page, scroll depth]
- Content Downloads: [Number]

## Campaign Performance
- Active Campaigns: [Number]
- Campaign ROI: [X]%
- Best Performing Campaign: [Name and metrics]
- Campaigns to Optimize: [List]

## Goals vs Actual
- [Goal 1]: [Target] vs [Actual] - [Status]
- [Goal 2]: [Target] vs [Actual] - [Status]
- [Goal 3]: [Target] vs [Actual] - [Status]
```
