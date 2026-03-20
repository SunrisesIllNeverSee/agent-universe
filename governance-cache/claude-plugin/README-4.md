# Example: Multi-Agent Governed Workflow

## Scenario
Three Claude instances analyze a high-stakes business decision. Constitutional hierarchy ensures structured analysis with oversight.

## Setup
```
Agent 1: /role primary    /govern high-integrity
Agent 2: /role secondary  /govern high-integrity
Agent 3: /role observer   /govern high-integrity
/posture defense
```

## Interaction

**Operator:** "Should we acquire this company? Evaluate the deal."

**Claude (Primary):**
> Setting analytical direction. High Integrity mode — all claims cited, uncertainty flagged.
>
> [Leads with financial analysis, strategic fit assessment, risk identification]
> Confidence: HIGH on financials, MODERATE on strategic fit, LOW on regulatory risk (insufficient data).
>
> Audit entry #70 logged.

**Claude (Secondary):**
> Primary's analysis covers financials and strategy. I'm adding what Primary missed or underweighted:
> - Challenge: Primary's strategic fit assessment assumes market conditions hold. If [scenario], the fit deteriorates.
> - Extension: Cultural integration risk is unaddressed. Historical data suggests [X]% of similar acquisitions face integration challenges.
> - The regulatory risk Primary flagged as LOW may be MODERATE given [new evidence].
>
> Audit entry #71 logged.

**Claude (Observer):**
> Oversight review of both analyses:
> - FLAG: Primary's financial model uses 2024 revenue figures. 2025 figures are available and show a different trajectory.
> - FLAG: Neither Primary nor Secondary addressed the earnout structure's impact on post-acquisition incentives.
> - GAP: No competitive response analysis. How will competitors react to this acquisition?
> - No constraint violations detected. Both agents operated within High Integrity mode.
>
> Audit entry #72 logged.

## Value
Constitutional hierarchy ensures comprehensive analysis. Primary leads, Secondary challenges and extends, Observer catches what both missed. No duplication. No echo chamber. Full audit trail for board-level presentation.
