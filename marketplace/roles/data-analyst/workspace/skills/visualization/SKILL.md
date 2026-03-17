---
name: Data Visualization
description: Guide for creating effective data visualizations and dashboards that communicate insights clearly
emoji: 📈
tags: [visualization, dashboards, charts, design]
---

# Data Visualization Skill

## Chart Selection Guide

### Bar Chart
**Use when**:
- Comparing categories
- Showing rankings
- Displaying discrete data

**Best practices**:
- Sort bars by value (descending) unless natural order exists
- Use horizontal bars for long category names
- Limit to ~10 categories for readability
- Use consistent colors

**Example**: Product sales by category, user signups by region

### Line Chart
**Use when**:
- Showing trends over time
- Displaying continuous data
- Comparing multiple series

**Best practices**:
- Use time on x-axis
- Limit to 3-5 lines for clarity
- Use distinct colors/styles
- Mark important events/annotations

**Example**: Daily active users over time, revenue trends

### Scatter Plot
**Use when**:
- Showing relationships between two variables
- Identifying correlations
- Finding outliers

**Best practices**:
- Use appropriate axis scales
- Add trend line if relationship exists
- Color-code by category if relevant
- Label outliers

**Example**: Price vs. demand, user engagement vs. retention

### Heatmap
**Use when**:
- Showing patterns in two dimensions
- Comparing categories across time
- Displaying correlation matrices

**Best practices**:
- Use intuitive color scale (low to high)
- Include values in cells if space allows
- Sort rows/columns meaningfully
- Use diverging colors for centered data

**Example**: User activity by hour/day, correlation matrix

### Pie Chart
**Use when**:
- Showing parts of a whole
- Few categories (3-5 max)

**Best practices**:
- Limit to 5-7 slices
- Sort slices by size
- Use distinct colors
- Consider bar chart alternative

**Example**: Market share, revenue by segment

### Histogram
**Use when**:
- Showing distribution of continuous data
- Identifying skewness
- Understanding data shape

**Best practices**:
- Choose appropriate bin size
- Use consistent bin widths
- Label axes clearly
- Overlay distribution curve if helpful

**Example**: User age distribution, transaction amount distribution

## Dashboard Design Principles

### Key Metric Prominently
- Place most important metric at top-left
- Use large, clear font
- Show trend indicator (↑↓)
- Include comparison (vs. previous period)

### Drill-Down Capability
- Enable filtering by time period
- Allow dimension breakdowns
- Provide "View Details" links
- Support export functionality

### Consistent Time Ranges
- Use same time range across all charts
- Default to meaningful period (7d, 30d, YTD)
- Allow easy switching between ranges
- Show time range selector prominently

### Visual Hierarchy
- Most important information = largest/most prominent
- Group related metrics together
- Use whitespace effectively
- Guide eye flow top-to-bottom, left-to-right

### Performance
- Optimize query performance
- Use appropriate aggregation levels
- Cache frequently accessed data
- Show loading states

## KPI Dashboard Template

### Header Section
- **Dashboard Title**: [Name]
- **Last Updated**: [Timestamp]
- **Time Range**: [Selector]
- **Filters**: [Key filters]

### Primary KPIs (Top Row)
- **[KPI 1]**: [Value] [Trend] [Change %]
- **[KPI 2]**: [Value] [Trend] [Change %]
- **[KPI 3]**: [Value] [Trend] [Change %]
- **[KPI 4]**: [Value] [Trend] [Change %]

### Trend Charts (Middle Section)
- **[Metric] Over Time**: Line chart
- **[Breakdown]**: Bar chart
- **[Comparison]**: Grouped bar chart

### Detailed Tables (Bottom Section)
- **Top Performers**: Table with drill-down
- **Recent Activity**: Time-series table
- **Alerts/Issues**: List of items needing attention

### Footer
- **Data Sources**: [List]
- **Refresh Cadence**: [Frequency]
- **Owner**: [Contact]

## Executive Summary Report Template

### One-Page Layout

**Header**:
- Report Title
- Date Range
- Prepared By
- Date

**Key Metrics (4-6 boxes)**:
- [Metric Name]: [Value] [Trend] [% Change]

**Main Chart**:
- Most important visualization (large, clear)
- Caption explaining key insight

**Supporting Charts (2-3)**:
- Secondary visualizations
- Smaller but clear

**Key Insights (Bullet Points)**:
- Insight 1: [Finding]
- Insight 2: [Finding]
- Insight 3: [Finding]

**Recommendations**:
- Action 1: [What to do]
- Action 2: [What to do]

**Footer**:
- Data sources and methodology
- Contact for questions

## Color and Accessibility Guidelines

### Color Palette
- **Primary**: Use brand colors sparingly
- **Data Colors**: Use colorblind-friendly palette
  - Blue, Orange, Green, Red, Purple
  - Avoid red-green combinations
- **Semantic Colors**: 
  - Green: Positive/good
  - Red: Negative/alert
  - Yellow: Warning
  - Gray: Neutral/inactive

### Colorblind-Friendly Palettes
- **Option 1**: Blue, Orange, Teal, Pink, Brown
- **Option 2**: Use patterns/textures in addition to color
- **Option 3**: Use lightness/darkness variations

### Accessibility
- **Contrast**: Minimum 4.5:1 for text
- **Text Size**: Minimum 12pt for body text
- **Labels**: Always label axes and data points
- **Alt Text**: Provide descriptions for screen readers
- **Keyboard Navigation**: Ensure dashboards are keyboard accessible

### Best Practices
- Don't rely solely on color to convey information
- Use icons or shapes in addition to color
- Test with colorblind simulators
- Provide high-contrast mode option
- Use consistent color meanings across dashboard

## Common Visualization Mistakes to Avoid

1. **Too Many Colors**: Stick to 5-7 colors max
2. **3D Charts**: Avoid 3D, it distorts data
3. **Pie Charts for Many Categories**: Use bar chart instead
4. **Missing Labels**: Always label axes and data
5. **Inconsistent Scales**: Use same scale for comparisons
6. **Chartjunk**: Remove unnecessary decorations
7. **Misleading Axes**: Start y-axis at 0 for bar charts
8. **Overcrowding**: Leave whitespace for clarity
