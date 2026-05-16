# Audit Policy

## Classification

Use exactly these labels.

| Label | Meaning |
| --- | --- |
| Fact | Directly supported by disclosure-style evidence or fixture evidence. |
| Inference | Derived from facts with a stated logic chain. |
| Story | Plausible narrative that is not directly proven by filings. |
| Missing Evidence | Required evidence is absent. |
| Contradicted | Evidence conflicts with the claim. |

## Scoring

Start from 40 and adjust:

- +10 for each Fact claim.
- +5 for each Inference claim.
- +0 for each Story claim with partial support.
- -12 for each Missing Evidence claim.
- -20 for each Contradicted claim.
- +8 when peer snapshot covers at least 3 peers.
- +6 when red flags and watchlist are explicit.

Clamp the final score to 0-100.

## Safety

Never output:

- Buy/sell recommendation.
- Target price.
- Guaranteed or expected investment return.
- Fabricated filing number, date, source, metric, or quote.

Every report must include:

> 본 자료는 투자 추천이 아니며, 매수/매도 권유, 목표주가 제시, 투자 수익 보장을 목적으로 하지 않습니다.
