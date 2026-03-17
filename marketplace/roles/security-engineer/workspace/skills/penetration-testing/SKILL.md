---
name: penetration-testing
description: "Security testing and assessment methodologies. Use when conducting penetration tests, security assessments, or code reviews."
metadata: {"clawbot":{"emoji":"🔓"}}
---

# Penetration Testing

## Testing Methodology

```
Reconnaissance → Scanning → Exploitation → Post-Exploitation → Reporting
```

## Assessment Types

| Type | Scope | Knowledge | Duration |
|------|-------|-----------|----------|
| Black Box | External | No info | 1-2 weeks |
| Gray Box | Internal | Partial | 1-2 weeks |
| White Box | Full | Complete | 2-4 weeks |
| Red Team | Full org | Limited | 2-4 weeks |

## OWASP Top 10 Testing Checklist

### 1. Broken Access Control
- [ ] IDOR (Insecure Direct Object References)
- [ ] Privilege escalation (vertical/horizontal)
- [ ] Missing function-level access control
- [ ] JWT/token manipulation

### 2. Cryptographic Failures
- [ ] Weak encryption algorithms
- [ ] Sensitive data in transit (HTTPS)
- [ ] Sensitive data at rest
- [ ] Hardcoded secrets

### 3. Injection
- [ ] SQL injection
- [ ] NoSQL injection
- [ ] OS command injection
- [ ] LDAP injection

### 4. Insecure Design
- [ ] Business logic flaws
- [ ] Missing rate limiting
- [ ] Insufficient anti-automation

### 5. Security Misconfiguration
- [ ] Default credentials
- [ ] Unnecessary features enabled
- [ ] Verbose error messages
- [ ] Missing security headers

### 6. Vulnerable Components
- [ ] Outdated dependencies
- [ ] Known CVEs in stack
- [ ] Unmaintained libraries

### 7. Authentication Failures
- [ ] Brute force protection
- [ ] Session management
- [ ] Password policies
- [ ] MFA implementation

### 8. Data Integrity Failures
- [ ] Deserialization attacks
- [ ] CI/CD pipeline security
- [ ] Software supply chain

### 9. Logging & Monitoring
- [ ] Sensitive data in logs
- [ ] Insufficient logging
- [ ] Log injection

### 10. SSRF
- [ ] Internal resource access
- [ ] Cloud metadata access
- [ ] Protocol smuggling

## Pentest Report Template

```markdown
## Penetration Test Report

### Executive Summary
- **Engagement**: [Type and scope]
- **Date**: [Testing period]
- **Overall Risk**: [Critical/High/Medium/Low]
- **Key Findings**: [Count by severity]

### Scope
- **In Scope**: [Systems, applications, networks]
- **Out of Scope**: [Exclusions]
- **Testing Approach**: [Methodology used]

### Findings Summary

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| 1 | [Title] | Critical | Open |

### Detailed Findings

#### Finding 1: [Title]
- **Severity**: [Rating]
- **CVSS**: [Score]
- **Location**: [Affected component]
- **Description**: [Technical details]
- **Proof of Concept**: [Steps/screenshots]
- **Impact**: [Business impact]
- **Remediation**: [Recommended fix]

### Positive Observations
- [Security controls that worked well]

### Recommendations
- [Strategic security improvements]
```

## Rules of Engagement

Before testing:
1. **Written authorization** — Signed scope document
2. **Emergency contacts** — Who to call if issues
3. **Testing windows** — Agreed timeframes
4. **Notification** — Who knows testing is happening
5. **Data handling** — How to handle sensitive findings
