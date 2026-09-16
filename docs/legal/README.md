# Regulatory References & Statutory Sources

This directory establishes the authoritative regulatory reference framework for PackCheck. It ensures that all compliance evaluations performed by the system remain strictly traceable to official Legal Metrology statutes, gazette notifications, and amendments.

---

## Traceability & Governance Principles

1. **Authoritative Source Traceability**:
   - All compliance rules evaluated by the PackCheck Rule Engine must be directly traceable to primary, authoritative Legal Metrology sources (such as the Legal Metrology Act, 2009 and the Legal Metrology (Packaged Commodities) Rules, 2011).
   - Compliance logic must not be derived from secondary commentaries, informal interpretations, or unverified blog posts.

2. **Mandatory Rule Record Requirements**:
   Every implemented rule check in the codebase must explicitly record and cite:
   - **Rule Identifier**: Canonical, stable identifier (e.g., `LMR-2011-R06`).
   - **Source Document**: Official statutory title (e.g., *Legal Metrology (Packaged Commodities) Rules, 2011*).
   - **Source / Version or Amendment Reference**: Exact clause, gazette notification number, and publication/effective date.
   - **Implementation Reference**: Path to the specific deterministic Python module enforcing the rule.

3. **Explicit Amendment Tracking**:
   - Amendments must be tracked as distinct, versioned records rather than silently modifying or replacing previous statutory baselines.
   - The system must preserve the statutory timeline so that package evaluations can deterministically reference the rules in force at the date of packaging or manufacture.

4. **Prohibition of Silent Replacement**:
   - An authoritative regulatory source must never be silently replaced, modified, or superseded by an unofficial, unverified, or secondary source.
   - Any modification or addition to regulatory source documents must be auditable and backed by official government publication records.

5. **Structural Separation of Concerns**:
   The repository strictly distinguishes between three tiers of material:
   - **Authoritative Source Documents** (`docs/legal/sources/`): Unmodified official statutes, gazette notifications, and regulatory publications.
   - **Implementation Notes** (`docs/legal/` or `rules/` documentation): Developer summaries, parameter mappings, and schema translation guides that reference authoritative sources.
   - **Test Fixtures** (`data/`, `tests/`): Synthetic or sample package declarations used to verify rule engines against expected outcomes without acting as statutory definitions.

---

## Directory Structure

```text
docs/legal/
├── README.md              # Governance principles and traceability standards (this file)
└── sources/               # Authoritative primary source files and gazette notifications
```
