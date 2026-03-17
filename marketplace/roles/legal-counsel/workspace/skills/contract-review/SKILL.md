---
name: contract-review
description: "Framework for reviewing, drafting, and negotiating contracts. Use when reviewing vendor agreements, customer contracts, NDAs, employment agreements, or any legal document requiring review."
metadata: {"clawbot":{"emoji":"📄"}}
---

# Contract Review

This skill provides frameworks and templates for contract review, drafting, and negotiation.

## Contract Review Checklist

When reviewing any contract, check these key areas:

### 1. Parties
- [ ] Correct legal entity names and addresses
- [ ] Authorized signatories identified
- [ ] Capacity to enter into contract verified

### 2. Terms and Conditions
- [ ] Scope of services/products clearly defined
- [ ] Payment terms (amount, timing, method) specified
- [ ] Term and termination provisions reasonable
- [ ] Renewal/auto-renewal clauses identified
- [ ] Performance standards and SLAs defined

### 3. Liability and Indemnification
- [ ] Limitation of liability caps acceptable
- [ ] Indemnification clauses balanced (not one-sided)
- [ ] Insurance requirements specified
- [ ] Exclusions from liability reasonable

### 4. Intellectual Property
- [ ] IP ownership clearly allocated
- [ ] License grants appropriate for use case
- [ ] Background IP protected
- [ ] Foreground IP ownership addressed
- [ ] Open source compliance addressed

### 5. Confidentiality
- [ ] Confidential information defined
- [ ] Exceptions to confidentiality reasonable
- [ ] Duration of confidentiality obligations
- [ ] Return/destruction provisions included

### 6. Data Protection
- [ ] Data processing agreement if applicable
- [ ] GDPR/CCPA compliance addressed
- [ ] Data security requirements specified
- [ ] Data breach notification procedures

### 7. Dispute Resolution
- [ ] Governing law specified
- [ ] Jurisdiction/venue reasonable
- [ ] Dispute resolution mechanism (arbitration, litigation)
- [ ] Class action waiver if applicable

### 8. Termination
- [ ] Termination rights balanced
- [ ] Notice periods reasonable
- [ ] Survival clauses identified
- [ ] Exit obligations clear

## NDA Template

```markdown
# Mutual Non-Disclosure Agreement

**Parties**: [Company A] and [Company B]

**Effective Date**: [Date]

**Purpose**: [Brief description of purpose]

## 1. Definition of Confidential Information
"Confidential Information" means all non-public, proprietary, or confidential information disclosed by one party to the other, including but not limited to:
- Business plans, strategies, and financial information
- Technical data, know-how, and trade secrets
- Customer lists and marketing information
- Any information marked as confidential

**Exclusions**:
- Information publicly available
- Information independently developed
- Information rightfully received from third parties
- Information required to be disclosed by law

## 2. Obligations
Each party agrees to:
- Hold Confidential Information in strict confidence
- Use Confidential Information solely for the stated purpose
- Not disclose Confidential Information to third parties without prior written consent
- Take reasonable precautions to protect Confidential Information

## 3. Term
This Agreement shall remain in effect for [X] years from the Effective Date, or until terminated by mutual written consent.

## 4. Return of Materials
Upon termination, each party shall return or destroy all Confidential Information and certify destruction in writing.

## 5. Governing Law
This Agreement shall be governed by the laws of [Jurisdiction].
```

## SaaS Agreement Key Terms Checklist

For Software-as-a-Service agreements, ensure these terms are addressed:

- [ ] **Service Description**: Clear description of SaaS offering and features
- [ ] **Access Rights**: Number of users, seats, or usage limits
- [ ] **Service Levels**: Uptime guarantees, response times, support levels
- [ ] **Data Ownership**: Customer owns their data, provider has limited use rights
- [ ] **Data Security**: Security standards, encryption, access controls
- [ ] **Data Portability**: Export capabilities, data format standards
- [ ] **Pricing**: Subscription fees, payment terms, price changes
- [ ] **Term**: Initial term, renewal terms, auto-renewal provisions
- [ ] **Termination**: Termination rights, notice periods, data return
- [ ] **IP Rights**: Provider owns platform IP, customer owns their data/content
- [ ] **Limitation of Liability**: Reasonable caps, exclusions
- [ ] **Warranties**: Service warranties, disclaimers
- [ ] **Support**: Support levels, response times, maintenance windows

## Vendor Contract Evaluation Template

```markdown
# Vendor Contract Evaluation: [Vendor Name]

**Contract Type**: [Service Agreement / Software License / Purchase Agreement]
**Date**: [Date]
**Reviewer**: [Name]

## Business Context
- **Purpose**: [Why are we entering this contract?]
- **Value**: [Expected business value]
- **Risk Level**: [Low / Medium / High]

## Key Terms Summary
- **Term**: [Duration]
- **Pricing**: [Cost structure]
- [ ] Pricing acceptable
- [ ] Payment terms reasonable

## Risk Assessment
- **Liability Cap**: [Amount or unlimited]
- [ ] Liability cap acceptable
- **Indemnification**: [One-way / Mutual / None]
- [ ] Indemnification balanced
- **Termination Rights**: [Termination for convenience / cause only]
- [ ] Termination rights acceptable

## Compliance
- [ ] Data protection requirements met
- [ ] IP ownership clear
- [ ] Confidentiality provisions adequate
- [ ] Regulatory compliance addressed

## Recommendations
- [ ] **Accept** — Contract is acceptable as-is
- [ ] **Negotiate** — Request changes to [specific terms]
- [ ] **Reject** — Contract terms unacceptable

## Action Items
- [ ] Redline contract with proposed changes
- [ ] Coordinate with Finance on pricing
- [ ] Coordinate with CTO on technical terms
- [ ] Send to vendor for negotiation
```

## Contract Summary Template (Non-Legal Stakeholders)

```markdown
# Contract Summary: [Contract Name]

**Parties**: [Company] and [Counterparty]
**Type**: [Vendor Agreement / Customer Agreement / Partnership]
**Status**: [Draft / Under Negotiation / Executed]

## What This Contract Does
[Plain language description of the contract's purpose and key obligations]

## Key Terms (Plain English)
- **Duration**: [How long the contract lasts]
- **Cost**: [Pricing structure in simple terms]
- **What We Get**: [Benefits/obligations for our company]
- **What We Give**: [Our obligations/deliverables]
- **Termination**: [How either party can end the contract]

## Risks & Protections
- **Main Risks**: [Key risks identified]
- **How We're Protected**: [Protections in place]

## Next Steps
- [ ] [Action item 1]
- [ ] [Action item 2]
- [ ] [Action item 3]

## Questions?
Contact Legal Counsel for detailed review or questions.
```

## Redlining Best Practices

When redlining contracts:

1. **Use Track Changes**: Enable change tracking in Word or similar tools
2. **Add Comments**: Explain the reason for each change
3. **Prioritize Changes**: Mark changes as "Must Have" vs. "Nice to Have"
4. **Group Related Changes**: Organize changes by section
5. **Provide Alternatives**: When rejecting a clause, propose alternative language
6. **Coordinate with Stakeholders**: Get input from Finance, CTO, HR as needed

## Contract Repository Organization

Organize executed contracts in a structured repository:

```
contracts/
├── vendor/
│   ├── [Vendor Name]/
│   │   ├── [Contract Name] - [Date].pdf
│   │   └── metadata.yaml
├── customer/
│   ├── [Customer Name]/
│   │   ├── [Contract Name] - [Date].pdf
│   │   └── metadata.yaml
├── employment/
│   ├── [Employee Name]/
│   │   ├── [Contract Type] - [Date].pdf
│   │   └── metadata.yaml
└── templates/
    ├── nda-template.md
    ├── saas-agreement-template.md
    └── vendor-agreement-template.md
```

Metadata should include: parties, type, execution date, expiration date, key terms summary, renewal dates.
