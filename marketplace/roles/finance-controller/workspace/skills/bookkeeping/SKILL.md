---
name: bookkeeping
description: "Financial record keeping: chart of accounts, journal entries, monthly close, reconciliation, and invoice management. Use when maintaining financial records and closing books."
metadata: {"clawbot":{"emoji":"📚"}}
---

# Bookkeeping

## Chart of Accounts Template

Maintain a standardized chart of accounts organized by category:

### Assets
- 1000-1999: Current Assets
  - 1010: Cash - Operating Account
  - 1020: Cash - Reserve Account
  - 1100: Accounts Receivable
  - 1200: Prepaid Expenses
  - 1300: Inventory (if applicable)
- 2000-2999: Fixed Assets
  - 2010: Equipment
  - 2020: Accumulated Depreciation - Equipment
  - 2100: Software Licenses
  - 2200: Accumulated Amortization - Software

### Liabilities
- 3000-3999: Current Liabilities
  - 3010: Accounts Payable
  - 3020: Accrued Expenses
  - 3030: Short-term Debt
  - 3100: Deferred Revenue
- 4000-4999: Long-term Liabilities
  - 4010: Long-term Debt
  - 4100: Lease Obligations

### Equity
- 5000-5999: Equity
  - 5010: Common Stock
  - 5020: Additional Paid-in Capital
  - 5100: Retained Earnings

### Revenue
- 6000-6999: Revenue
  - 6010: Product Revenue
  - 6020: Service Revenue
  - 6100: Other Income

### Expenses
- 7000-7999: Cost of Goods Sold
  - 7010: Cost of Revenue
  - 7100: Infrastructure Costs
- 8000-8999: Operating Expenses
  - 8010: Salaries & Wages
  - 8020: Benefits
  - 8100: Rent
  - 8200: Utilities
  - 8300: Marketing & Advertising
  - 8400: Professional Services (Legal, Accounting)
  - 8500: Software & Subscriptions
  - 8600: Travel & Entertainment
  - 8700: Office Supplies
  - 8800: Insurance
  - 8900: Depreciation & Amortization
- 9000-9999: Other Expenses
  - 9010: Interest Expense
  - 9100: Taxes

## Journal Entry Format

Record all transactions using double-entry bookkeeping:

```markdown
### Journal Entry: {Description}
- **Date**: YYYY-MM-DD
- **Reference**: {Invoice # / Transaction ID}
- **Debit Account**: {Account Code} - {Account Name} | Amount: $X
- **Credit Account**: {Account Code} - {Account Name} | Amount: $X
- **Description**: {Detailed explanation}
- **Approved By**: {Name}
```

Example:
```markdown
### Journal Entry: Monthly SaaS Subscription
- **Date**: 2026-02-01
- **Reference**: INV-2026-001
- **Debit Account**: 8500 - Software & Subscriptions | Amount: $500
- **Credit Account**: 3010 - Accounts Payable | Amount: $500
- **Description**: Monthly subscription for cloud infrastructure tools
- **Approved By**: Finance Controller
```

## Monthly Close Checklist

Complete these tasks before closing each month:

- [ ] All transactions recorded and posted
- [ ] Bank accounts reconciled
- [ ] Credit card accounts reconciled
- [ ] Accounts receivable reviewed and aged
- [ ] Accounts payable reviewed and aged
- [ ] Prepaid expenses reviewed and amortized
- [ ] Accrued expenses recorded
- [ ] Depreciation calculated and posted
- [ ] Amortization calculated and posted
- [ ] Deferred revenue reviewed and recognized
- [ ] Intercompany transactions eliminated (if applicable)
- [ ] Trial balance reviewed for errors
- [ ] Financial statements generated
- [ ] Budget vs actual variance analysis completed
- [ ] Close date documented in accounting system

## Reconciliation Procedure

### Bank Reconciliation

1. Obtain bank statement for the period
2. Compare bank statement to general ledger cash account
3. Identify and document:
   - Outstanding checks (not yet cleared)
   - Deposits in transit (not yet recorded by bank)
   - Bank fees and charges
   - Interest earned
   - NSF checks or other adjustments
4. Prepare reconciliation statement showing:
   - Bank balance per statement
   - Add: Deposits in transit
   - Less: Outstanding checks
   - Add/Less: Other adjustments
   - Equals: Adjusted bank balance
   - General ledger balance
   - Add/Less: Adjustments
   - Equals: Adjusted general ledger balance
   - Both adjusted balances must match
5. Document any discrepancies and resolve
6. File reconciliation with supporting documents

### Credit Card Reconciliation

1. Obtain credit card statement
2. Match each charge to receipt/invoice
3. Verify business purpose for each expense
4. Code expenses to appropriate accounts
5. Reconcile statement balance to general ledger
6. Flag any unauthorized or unusual charges

## Invoice Template

When creating invoices for customers:

```markdown
# Invoice

**Invoice Number**: INV-YYYY-###
**Date**: YYYY-MM-DD
**Due Date**: YYYY-MM-DD

**Bill To**:
{Company Name}
{Address}

**Description**:
- {Item/Service} | Quantity: X | Rate: $X | Amount: $X
- {Item/Service} | Quantity: X | Rate: $X | Amount: $X

**Subtotal**: $X
**Tax**: $X (if applicable)
**Total**: $X

**Payment Terms**: Net 30
**Payment Instructions**: {Bank details / Payment link}
```

## Record Retention

- **Invoices**: 7 years
- **Bank Statements**: 7 years
- **Tax Returns**: 7 years (permanent for some entities)
- **Financial Statements**: Permanent
- **Contracts**: Duration of contract + 7 years
- **Payroll Records**: 7 years
