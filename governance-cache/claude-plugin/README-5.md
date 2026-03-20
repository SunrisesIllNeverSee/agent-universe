# Example: Governed Code Review

## Scenario
A development team uses Claude for code review. With MO§E§™, the review follows structured governance with role hierarchy.

## Setup
```
/govern high-integrity
/posture scout
/role primary
```

## Interaction

**Operator:** "Review this pull request for security vulnerabilities."

**Claude (Primary, governed):**
> High Integrity mode active — I will cite specific lines, flag uncertainty levels, and distinguish confirmed vulnerabilities from potential risks.
> SCOUT posture — analysis only, I will not modify any files.
>
> [Detailed analysis with citations, confidence levels, and flagged uncertainties]
>
> Audit entry #31 logged.

**Secondary agent reads Primary's review:**
```
/role secondary
```

**Claude (Secondary, governed):**
> Building on Primary's analysis. Primary identified 3 confirmed vulnerabilities and 2 potential risks. I'm adding:
> - One additional vulnerability Primary missed in the authentication middleware
> - A challenge to Primary's assessment of risk #2 — I believe the severity is higher because [reasoning]
> - An extension: the identified SQL injection pattern also appears in two other endpoints
>
> Audit entry #32 logged.

## Value
Structured review with constitutional quality controls. Primary leads, Secondary validates and extends. High Integrity mode ensures accuracy. SCOUT posture ensures no accidental modifications. Full audit trail for compliance.
