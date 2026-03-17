---
name: risk-assessment
description: "Framework for legal risk assessment and management. Use when evaluating legal risks, managing risk registers, assessing IP protection needs, or conducting risk reviews."
metadata: {"clawbot":{"emoji":"⚠️"}}
---

# Risk Assessment

This skill provides frameworks for identifying, assessing, and managing legal risks.

## Risk Register Template

```markdown
# Legal Risk Register

| ID | Risk Description | Category | Likelihood | Impact | Risk Score | Status | Owner | Mitigation Strategy | Next Review |
|----|------------------|----------|------------|--------|------------|--------|-------|---------------------|-------------|
| LR-001 | [Risk description] | [Contract/IP/Compliance/etc.] | [Low/Med/High] | [Low/Med/High] | [1-9] | [Open/Mitigated/Closed] | [Name] | [Strategy] | [Date] |
```

### Risk Categories
- **Contract**: Contract-related risks (unfavorable terms, breach risk)
- **IP**: Intellectual property risks (infringement, misappropriation)
- **Compliance**: Regulatory compliance risks (GDPR, employment law)
- **Litigation**: Dispute and litigation risks
- **Employment**: Employment law risks (wrongful termination, discrimination)
- **Data**: Data protection and privacy risks
- **Corporate**: Corporate governance risks

### Risk Scoring Matrix

**Likelihood**:
- **Low (1)**: Unlikely to occur (< 10% probability)
- **Medium (2)**: Possible to occur (10-50% probability)
- **High (3)**: Likely to occur (> 50% probability)

**Impact**:
- **Low (1)**: Minimal impact (minor financial loss, no operational impact)
- **Medium (2)**: Moderate impact (significant financial loss, some operational impact)
- **High (3)**: Severe impact (major financial loss, significant operational impact, reputational damage)

**Risk Score = Likelihood × Impact**

- **1-2**: Low Risk — Accept or monitor
- **3-4**: Medium Risk — Mitigate or transfer
- **6-9**: High Risk — Mitigate immediately or avoid

### Risk Response Strategies

1. **Accept**: Risk is acceptable, no action needed
2. **Mitigate**: Implement controls to reduce likelihood or impact
3. **Transfer**: Use insurance, indemnification, or contracts to transfer risk
4. **Avoid**: Eliminate the risk by changing approach or declining opportunity

## IP Protection Checklist

### Patents
- [ ] **Invention Disclosure**: Document inventions promptly
- [ ] **Prior Art Search**: Conduct search before filing
- [ ] **Patentability Assessment**: Evaluate novelty, non-obviousness, utility
- [ ] **Filing Strategy**: Determine filing jurisdictions and timing
- [ ] **Patent Applications**: File provisional or non-provisional applications
- [ ] **Maintenance**: Pay maintenance fees to keep patents in force
- [ ] **Infringement Monitoring**: Monitor for potential infringement
- [ ] **Freedom to Operate**: Assess FTO before product launch

### Trademarks
- [ ] **Trademark Search**: Conduct clearance search before use
- [ ] **Registration**: File trademark applications in key jurisdictions
- [ ] **Use Requirements**: Maintain proper use to avoid abandonment
- [ ] **Renewal**: File renewal applications before expiration
- [ ] **Monitoring**: Monitor for unauthorized use or infringement
- [ ] **Enforcement**: Take action against infringers when necessary

### Copyrights
- [ ] **Copyright Notice**: Include copyright notices on works
- [ ] **Registration**: Register copyrights for key works (optional but recommended)
- [ ] **Ownership**: Ensure proper assignment from creators
- [ ] **License Management**: Track licenses granted and received
- [ ] **Infringement Monitoring**: Monitor for unauthorized use

### Trade Secrets
- [ ] **Identification**: Identify information that qualifies as trade secrets
- [ ] **Documentation**: Document trade secret policies and procedures
- [ ] **Access Controls**: Limit access to trade secret information
- [ ] **Confidentiality Agreements**: Require NDAs for employees and third parties
- [ ] **Physical Security**: Secure physical storage of trade secrets
- [ ] **Digital Security**: Encrypt and secure digital trade secrets
- [ ] **Employee Training**: Train employees on trade secret protection
- [ ] **Exit Procedures**: Secure return of trade secrets upon employee departure

### Open Source Compliance
- [ ] **License Inventory**: Identify all open source components used
- [ ] **License Compatibility**: Ensure license compatibility
- [ ] **Attribution Requirements**: Comply with attribution requirements
- [ ] **Source Code Disclosure**: Understand when source code must be disclosed
- [ ] **Compliance Program**: Implement open source compliance program
- [ ] **Audit**: Regular audits of open source usage

## Litigation Hold Procedure

When litigation is reasonably anticipated, implement a litigation hold:

### 1. Identify Scope
- [ ] Identify relevant time period
- [ ] Identify relevant custodians (employees with relevant information)
- [ ] Identify relevant data sources (email, documents, systems)

### 2. Issue Hold Notice
- [ ] Draft litigation hold notice
- [ ] Distribute to all relevant custodians
- [ ] Obtain acknowledgment of receipt
- [ ] Provide instructions on preservation

### 3. Preserve Evidence
- [ ] Suspend automatic deletion policies
- [ ] Preserve relevant documents and data
- [ ] Preserve relevant systems and backups
- [ ] Document preservation actions

### 4. Monitor Compliance
- [ ] Regular follow-up with custodians
- [ ] Verify preservation measures
- [ ] Update hold as scope changes

### 5. Document Process
- [ ] Document all hold procedures
- [ ] Maintain records of notices sent
- [ ] Track compliance

## Insurance Coverage Review Template

```markdown
# Insurance Coverage Review

**Review Date**: [Date]
**Reviewer**: [Name]
**Policy Period**: [Start Date] to [End Date]

## Policies Reviewed

### General Liability
- **Carrier**: [Insurance Company]
- **Policy Number**: [Number]
- **Coverage Limits**: [Amount]
- **Deductible**: [Amount]
- **Expiration**: [Date]
- [ ] Coverage adequate for operations
- [ ] Renewal needed: [Date]

### Professional Liability / E&O
- **Carrier**: [Insurance Company]
- **Policy Number**: [Number]
- **Coverage Limits**: [Amount]
- **Deductible**: [Amount]
- **Expiration**: [Date]
- [ ] Coverage adequate for services provided
- [ ] Claims-made vs. occurrence policy understood
- [ ] Tail coverage considered if claims-made
- [ ] Renewal needed: [Date]

### Cyber Liability
- **Carrier**: [Insurance Company]
- **Policy Number**: [Number]
- **Coverage Limits**: [Amount]
- **Deductible**: [Amount]
- **Expiration**: [Date]
- [ ] Coverage includes data breach response
- [ ] Coverage includes business interruption
- [ ] Coverage adequate for data exposure
- [ ] Renewal needed: [Date]

### Directors & Officers (D&O)
- **Carrier**: [Insurance Company]
- **Policy Number**: [Number]
- **Coverage Limits**: [Amount]
- **Deductible**: [Amount]
- **Expiration**: [Date]
- [ ] Coverage adequate for board size and risk
- [ ] Side A/B/C coverage understood
- [ ] Renewal needed: [Date]

### Employment Practices Liability (EPLI)
- **Carrier**: [Insurance Company]
- **Policy Number**: [Number]
- **Coverage Limits**: [Amount]
- **Deductible**: [Amount]
- **Expiration**: [Date]
- [ ] Coverage includes discrimination, harassment, wrongful termination
- [ ] Coverage adequate for employee count
- [ ] Renewal needed: [Date]

## Coverage Gaps Identified
- [Gap 1]
- [Gap 2]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]

## Action Items
- [ ] [Action 1] — Owner: [Name] — Due: [Date]
- [ ] [Action 2] — Owner: [Name] — Due: [Date]

## Next Review
- Scheduled: [Date]
```

## Risk Assessment Workflow

1. **Identify Risks**: Brainstorm potential legal risks across all areas
2. **Categorize**: Assign risk to appropriate category
3. **Assess**: Score likelihood and impact
4. **Prioritize**: Focus on high-risk items first
5. **Respond**: Choose appropriate response strategy
6. **Document**: Record in risk register
7. **Monitor**: Regularly review and update risk register
8. **Report**: Communicate high risks to leadership

## Risk Review Schedule

- **Daily**: Monitor for new risks, review urgent matters
- **Weekly**: Review risk register, update status
- **Monthly**: Comprehensive risk review, update scores
- **Quarterly**: Risk register audit, strategy review
- **Annually**: Comprehensive risk assessment, insurance review
